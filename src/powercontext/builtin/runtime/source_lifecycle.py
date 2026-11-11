# Copyright (c) 2026 OceanBase.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Propagate Source withdrawal and restoration through the evidence DAG.

Callers register the Sources, Memory entries, and Topic Memory identities a
Scope depends on, then publish per-Source lifecycle events. Derived nodes are
evaluated with their parent policy (``all`` or ``any``) at registration and on
every propagated event. Generation may only see available nodes; audit always
resolves the originally registered reference.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr, field_validator

from powercontext.artifacts import ArtifactRef, MemoryCitation
from powercontext.builtin.artifacts.memory import Memory, MemoryEntryVersion, MemoryService
from powercontext.builtin.persistence.source_lifecycle import (
    SourceLifecycleNode,
    encode_reference,
    insert_node,
    load_nodes,
    save_availability,
    save_source_event,
)
from powercontext.builtin.sources import validate_scope_id
from powercontext.sources import SourceRef

if TYPE_CHECKING:
    from powercontext.builtin.runtime.application import BuiltinRuntime

_SOURCE = "source"
_MEMORY = "memory"
_TOPIC = "topic"
_PURPOSES = ("generation", "audit")


class SourceLifecycleError(ValueError):
    """Raised when a lifecycle registration, event, or resolution is invalid."""


class SourceLifecycleEvent(BaseModel):
    """One caller-declared availability change for an already registered Source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: StrictStr
    revision: StrictInt
    sequence: StrictInt
    available: StrictBool
    reason: StrictStr

    @field_validator("node_id", "reason")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty and not blank")  # noqa: TRY003
        return value

    @field_validator("revision", "sequence")
    @classmethod
    def require_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be a positive integer")  # noqa: TRY003
        return value


def _event_digest(event: SourceLifecycleEvent) -> str:
    material = json.dumps(
        {
            "available": event.available,
            "reason": event.reason,
            "revision": event.revision,
            "sequence": event.sequence,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _topological_order(nodes: Mapping[str, SourceLifecycleNode]) -> tuple[str, ...]:
    """Order registered nodes so every parent is evaluated before its children."""

    children: dict[str, list[str]] = {}
    indegree: dict[str, int] = {}
    for node in nodes.values():
        indegree.setdefault(node.node_id, 0)
        for parent in dict.fromkeys(node.parents):
            children.setdefault(parent, []).append(node.node_id)
            indegree[node.node_id] = indegree.get(node.node_id, 0) + 1
    ready = [node_id for node_id in nodes if indegree.get(node_id, 0) == 0]
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for child in children.get(current, ()):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if len(order) != len(nodes):
        raise SourceLifecycleError("dependency-cycle")
    return tuple(order)


def _propagate(
    nodes: Mapping[str, SourceLifecycleNode],
    source_id: str,
    available: bool,
) -> dict[str, bool]:
    """Re-evaluate every node from the new Source state in dependency order."""

    values = {node_id: node.available for node_id, node in nodes.items()}
    values[source_id] = available
    for node_id in _topological_order(nodes):
        node = nodes[node_id]
        if node.kind == _SOURCE:
            continue
        support = tuple(values[parent] for parent in node.parents)
        values[node_id] = all(support) if node.policy == "all" else any(support)
    return values


def _binding(node: SourceLifecycleNode) -> tuple[str, str | None, tuple[str, ...], str]:
    return (
        node.kind,
        node.policy,
        node.parents,
        encode_reference(node.reference),
    )


def _require_identifier(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceLifecycleError(code)
    return value


def _require_policy(value: object) -> Literal["all", "any"]:
    if value not in ("all", "any"):
        raise SourceLifecycleError("policy")
    return value  # type: ignore[return-value]


def _require_parents(node_id: str, parents: object, nodes: Mapping[str, SourceLifecycleNode]) -> tuple[str, ...]:
    if isinstance(parents, (str, bytes)) or not isinstance(parents, Sequence):
        raise SourceLifecycleError("parents")
    normalized = tuple(_require_identifier(parent, "parent") for parent in parents)
    if not normalized:
        raise SourceLifecycleError("parents-empty")
    if len(set(normalized)) != len(normalized):
        raise SourceLifecycleError("parents-duplicate")
    if node_id in normalized:
        raise SourceLifecycleError("parents-self")
    missing = [parent for parent in normalized if parent not in nodes]
    if missing:
        raise SourceLifecycleError("parent-unknown")
    return normalized


class SourceLifecycleApplication:
    """Select the Source lifecycle service for one Scope."""

    def __init__(self, runtime: BuiltinRuntime) -> None:
        self._runtime = runtime

    def for_scope(self, scope_id: str, /) -> ScopedSourceLifecycle:
        return ScopedSourceLifecycle(self._runtime, scope_id)


class ScopedSourceLifecycle:
    """Register and propagate the evidence dependency graph of one Scope."""

    def __init__(self, runtime: BuiltinRuntime, scope_id: str) -> None:
        self._runtime = runtime
        self.scope_id = validate_scope_id(scope_id)

    @property
    def _database(self):
        database = getattr(self._runtime._provider, "database", None)
        if database is None:
            raise SourceLifecycleError("persistence")
        return database

    async def register_source(self, node_id: str, reference: SourceRef, /, *, revision: int) -> None:
        node_id = _require_identifier(node_id, "node")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise SourceLifecycleError("revision")
        if not isinstance(reference, SourceRef):
            raise SourceLifecycleError("reference")
        try:
            record = await self._runtime.records.for_scope(self.scope_id).get_source(
                reference.source_type,
                reference.source_id,
            )
        except Exception as error:
            raise SourceLifecycleError("reference-unreadable") from error
        if record.source_type != reference.source_type or record.source_id != reference.source_id:
            raise SourceLifecycleError("reference-unreadable")
        candidate = SourceLifecycleNode(
            node_id=node_id,
            kind=_SOURCE,
            policy=None,
            parents=(),
            reference=reference.model_dump(mode="json"),
            revision=revision,
            sequence=None,
            event_digest=None,
            available=True,
            artifact_family=None,
            artifact_id=None,
        )
        await self._register(candidate)

    async def register_memory(
        self,
        node_id: str,
        citation: MemoryCitation,
        /,
        *,
        parents: Sequence[str],
        policy: Literal["all", "any"] = "all",
    ) -> None:
        node_id = _require_identifier(node_id, "node")
        normalized_policy = _require_policy(policy)
        if not isinstance(citation, MemoryCitation):
            raise SourceLifecycleError("reference")
        async with self._database.transaction() as connection:
            nodes = await load_nodes(connection, self.scope_id)
        normalized_parents = _require_parents(node_id, parents, nodes)
        available = _evaluate(nodes, normalized_parents, normalized_policy)
        candidate = SourceLifecycleNode(
            node_id=node_id,
            kind=_MEMORY,
            policy=normalized_policy,
            parents=normalized_parents,
            reference=citation.model_dump(mode="json"),
            revision=None,
            sequence=None,
            event_digest=None,
            available=available,
            artifact_family=citation.memory_ref.family,
            artifact_id=citation.memory_ref.artifact_id,
        )
        existing = nodes.get(node_id)
        if existing is not None:
            self._require_same_binding(existing, candidate)
            return
        async with self._runtime._context(self.scope_id) as context:
            service = context.artifacts.memory
            try:
                await service.validate_citation(citation)
                head = await service.head(citation.memory_ref.artifact_id)
            except Exception as error:
                raise SourceLifecycleError("reference-unreadable") from error
            if head.artifact_id != context.artifacts.memory_artifact_id:
                raise SourceLifecycleError("reference-unreadable")
            entry = await _head_entry(service, head, citation)
            await self._set_memory_state(service, head, entry, available)
        await self._insert(candidate)

    async def register_topic(
        self,
        node_id: str,
        reference: ArtifactRef,
        /,
        *,
        parents: Sequence[str],
        policy: Literal["all", "any"] = "all",
    ) -> None:
        node_id = _require_identifier(node_id, "node")
        normalized_policy = _require_policy(policy)
        if not isinstance(reference, ArtifactRef):
            raise SourceLifecycleError("reference")
        async with self._database.transaction() as connection:
            nodes = await load_nodes(connection, self.scope_id)
        normalized_parents = _require_parents(node_id, parents, nodes)
        try:
            await self._runtime.records.for_scope(self.scope_id).get_artifact_revision(
                reference.family,
                reference.artifact_id,
                reference.revision,
            )
        except Exception as error:
            raise SourceLifecycleError("reference-unreadable") from error
        available = _evaluate(nodes, normalized_parents, normalized_policy)
        candidate = SourceLifecycleNode(
            node_id=node_id,
            kind=_TOPIC,
            policy=normalized_policy,
            parents=normalized_parents,
            reference=reference.model_dump(mode="json"),
            revision=None,
            sequence=None,
            event_digest=None,
            available=available,
            artifact_family=reference.family,
            artifact_id=reference.artifact_id,
        )
        existing = nodes.get(node_id)
        if existing is not None:
            self._require_same_binding(existing, candidate)
            return
        await self._insert(candidate)

    async def apply(self, event: SourceLifecycleEvent, /) -> list[str]:
        if not isinstance(event, SourceLifecycleEvent):
            raise SourceLifecycleError("event")
        async with self._database.transaction() as connection:
            nodes = await load_nodes(connection, self.scope_id)
        source = nodes.get(event.node_id)
        if source is None or source.kind != _SOURCE:
            raise SourceLifecycleError("unknown-source")
        if source.revision != event.revision:
            raise SourceLifecycleError("revision-mismatch")
        digest = _event_digest(event)
        if source.sequence is not None:
            if event.sequence < source.sequence:
                raise SourceLifecycleError("sequence-regressed")
            if event.sequence == source.sequence:
                if source.event_digest != digest:
                    raise SourceLifecycleError("sequence-conflict")
                return _available_ids(nodes)

        targets = _propagate(nodes, event.node_id, event.available)
        changed = {
            node_id: available
            for node_id, available in targets.items()
            if nodes[node_id].available != available and nodes[node_id].kind == _MEMORY
        }
        if changed:
            await self._apply_memory_changes(nodes, changed)
        async with self._database.transaction() as connection:
            await save_availability(connection, self.scope_id, targets)
            await save_source_event(connection, self.scope_id, event.node_id, event.sequence, digest)
        return sorted(node_id for node_id, available in targets.items() if available)

    async def resolve(self, node_id: str, /, *, purpose: str) -> object:
        if not isinstance(purpose, str) or purpose not in _PURPOSES:
            raise SourceLifecycleError("purpose")
        async with self._database.transaction() as connection:
            nodes = await load_nodes(connection, self.scope_id)
        node = nodes.get(node_id)
        if node is None:
            raise SourceLifecycleError("unknown-node")
        if purpose == "generation" and not node.available:
            raise SourceLifecycleError("unavailable")
        return _reference(node)

    async def _insert(self, node: SourceLifecycleNode) -> None:
        async with self._database.transaction() as connection:
            await insert_node(connection, self.scope_id, node)

    async def _register(self, node: SourceLifecycleNode) -> None:
        async with self._database.transaction() as connection:
            nodes = await load_nodes(connection, self.scope_id)
            existing = nodes.get(node.node_id)
            if existing is not None:
                self._require_same_binding(existing, node)
                return
            await insert_node(connection, self.scope_id, node)

    @staticmethod
    def _require_same_binding(existing: SourceLifecycleNode, candidate: SourceLifecycleNode) -> None:
        if _binding(existing) != _binding(candidate):
            raise SourceLifecycleError("node-conflict")
        if existing.revision != candidate.revision:
            raise SourceLifecycleError("node-conflict")

    async def _apply_memory_changes(
        self,
        nodes: Mapping[str, SourceLifecycleNode],
        changed: Mapping[str, bool],
    ) -> None:
        async with self._runtime._context(self.scope_id) as context:
            service = context.artifacts.memory
            for node_id in sorted(changed):
                node = nodes[node_id]
                citation = MemoryCitation.model_validate(node.reference)
                try:
                    head = await service.head(citation.memory_ref.artifact_id)
                except Exception as error:
                    raise SourceLifecycleError("reference-unreadable") from error
                entry = await _head_entry(service, head, citation)
                await self._set_memory_state(service, head, entry, changed[node_id])

    @staticmethod
    async def _set_memory_state(
        service: MemoryService,
        head: Memory,
        entry: MemoryEntryVersion,
        available: bool,
    ) -> None:
        reason = "source-lifecycle-restore" if available else "source-lifecycle-withdraw"
        if available:
            await service.reactivate(head, entries=(entry,), reason=reason)
        else:
            await service.forget(head, entries=(entry,), reason=reason)


def _evaluate(
    nodes: Mapping[str, SourceLifecycleNode],
    parents: tuple[str, ...],
    policy: str,
) -> bool:
    support = tuple(nodes[parent].available for parent in parents)
    return all(support) if policy == "all" else any(support)


async def _head_entry(
    service: MemoryService,
    head: Memory,
    citation: MemoryCitation,
) -> MemoryEntryVersion:
    for entry in await service.entries(head):
        if entry.entry_id == citation.entry_id:
            return entry
    raise SourceLifecycleError("reference-unreadable")


def _available_ids(nodes: Mapping[str, SourceLifecycleNode]) -> list[str]:
    return sorted(node_id for node_id, node in nodes.items() if node.available)


def _reference(node: SourceLifecycleNode) -> object:
    if node.kind == _SOURCE:
        return SourceRef.model_validate(node.reference)
    if node.kind == _MEMORY:
        return MemoryCitation.model_validate(node.reference)
    return ArtifactRef.model_validate(node.reference)


__all__ = [
    "ScopedSourceLifecycle",
    "SourceLifecycleApplication",
    "SourceLifecycleError",
    "SourceLifecycleEvent",
]
