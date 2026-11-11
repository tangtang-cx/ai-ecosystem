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

"""Durable evidence-dependency graph and Source lifecycle state.

The graph is registered once per Scope and never rewritten; only the derived
availability of a node and the last accepted event of a Source change here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from powercontext.builtin.persistence.tables import SOURCE_LIFECYCLE_NODES_TABLE

_LIFECYCLE_NODES = SOURCE_LIFECYCLE_NODES_TABLE


@dataclass(frozen=True)
class SourceLifecycleNode:
    """One registered evidence node as persisted for a Scope."""

    node_id: str
    kind: str
    policy: str | None
    parents: tuple[str, ...]
    reference: dict[str, object]
    revision: int | None
    sequence: int | None
    event_digest: str | None
    available: bool
    artifact_family: str | None
    artifact_id: str | None


def encode_reference(reference: Mapping[str, object]) -> str:
    """Serialize a binding so equal registrations compare byte-identically."""

    return json.dumps(dict(reference), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def encode_parents(parents: tuple[str, ...]) -> str:
    return json.dumps(list(parents), separators=(",", ":"), ensure_ascii=False)


def _node(row: Mapping[object, object]) -> SourceLifecycleNode:
    return SourceLifecycleNode(
        node_id=str(row["node_id"]),
        kind=str(row["kind"]),
        policy=None if row["policy"] is None else str(row["policy"]),
        parents=tuple(json.loads(str(row["parents"]))),
        reference=json.loads(str(row["reference"])),
        revision=None if row["revision"] is None else int(row["revision"]),
        sequence=None if row["sequence"] is None else int(row["sequence"]),
        event_digest=None if row["event_digest"] is None else str(row["event_digest"]),
        available=bool(row["available"]),
        artifact_family=None if row["artifact_family"] is None else str(row["artifact_family"]),
        artifact_id=None if row["artifact_id"] is None else str(row["artifact_id"]),
    )


async def load_nodes(connection: AsyncConnection, scope_id: str, /) -> dict[str, SourceLifecycleNode]:
    """Read every registered node of one Scope in a stable order."""

    rows = (
        await connection.execute(
            select(_LIFECYCLE_NODES)
            .where(_LIFECYCLE_NODES.c.scope_id == scope_id)
            .order_by(_LIFECYCLE_NODES.c.node_id)
        )
    ).mappings()
    return {str(row["node_id"]): _node(row) for row in rows}


async def insert_node(
    connection: AsyncConnection,
    scope_id: str,
    node: SourceLifecycleNode,
    /,
) -> None:
    await connection.execute(
        insert(_LIFECYCLE_NODES).values(
            scope_id=scope_id,
            node_id=node.node_id,
            kind=node.kind,
            policy=node.policy,
            parents=encode_parents(node.parents),
            reference=encode_reference(node.reference),
            revision=node.revision,
            sequence=node.sequence,
            event_digest=node.event_digest,
            available=node.available,
            artifact_family=node.artifact_family,
            artifact_id=node.artifact_id,
        )
    )


async def save_availability(
    connection: AsyncConnection,
    scope_id: str,
    availability: Mapping[str, bool],
    /,
) -> None:
    """Persist derived node states after their native projections converged."""

    for node_id, available in availability.items():
        await connection.execute(
            update(_LIFECYCLE_NODES)
            .where(_LIFECYCLE_NODES.c.scope_id == scope_id, _LIFECYCLE_NODES.c.node_id == node_id)
            .values(available=available)
        )


async def save_source_event(
    connection: AsyncConnection,
    scope_id: str,
    node_id: str,
    sequence: int,
    event_digest: str,
    /,
) -> None:
    """Record the accepted event so a replay is recognized and a regression rejected."""

    await connection.execute(
        update(_LIFECYCLE_NODES)
        .where(_LIFECYCLE_NODES.c.scope_id == scope_id, _LIFECYCLE_NODES.c.node_id == node_id)
        .values(sequence=sequence, event_digest=event_digest)
    )


async def unavailable_topic_artifact_ids(connection: AsyncConnection, scope_id: str, /) -> frozenset[str]:
    """Return Topic Memory identities whose evidence no longer supports them."""

    rows = (
        await connection.execute(
            select(_LIFECYCLE_NODES.c.artifact_id).where(
                _LIFECYCLE_NODES.c.scope_id == scope_id,
                _LIFECYCLE_NODES.c.kind == "topic",
                _LIFECYCLE_NODES.c.available.is_(False),
            )
        )
    ).scalars()
    return frozenset(str(value) for value in rows if value is not None)


__all__ = [
    "SourceLifecycleNode",
    "encode_parents",
    "encode_reference",
    "insert_node",
    "load_nodes",
    "save_availability",
    "save_source_event",
    "unavailable_topic_artifact_ids",
]
