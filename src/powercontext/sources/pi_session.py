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

"""Capture the raw visible events of one Pi session branch.

A Pi session file stores a tree: every record names its parent and the selected
leaf decides which history is real for this run. This module keeps that history
as immutable Sources, one per visible event, so a later review can read the
original record and the exact tool output that produced it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, Field, JsonValue

from powercontext.limits import MAX_SOURCE_ID_LENGTH
from powercontext.sources import (
    TEXT_EVIDENCE_PROJECTION_KEY,
    AdapterSourceDefinition,
    ConnectorRunCompletion,
    ConnectorRunStatus,
    TextEvidence,
)
from powercontext.sources.models import Source, SourceMaterialization

PI_EVENT_SOURCE_NAME = "pi-event"
PI_SESSION_CONNECTOR_NAME = "pi-session-history"
PI_SESSION_CONNECTOR_VERSION = "1"
PI_SESSION_FORMAT_VERSION = 3
PI_EVENT_IDENTITY_PREFIX = "pi:"


class PiSessionInput(BaseModel):
    """One Pi session archive and the branch leaf to follow."""

    content: bytes
    leaf_id: str | None = None


class PiEventInput(BaseModel):
    """One visible event of the selected branch, with its original record."""

    session_id: str
    event_id: str
    parent_id: str | None = None
    event_type: str
    role: str
    content: str
    record: dict[str, JsonValue]


class PiEventSource(Source):
    """A captured Pi event that keeps its session identity and raw record."""

    source_id: str
    session_id: str
    event_id: str
    parent_id: str | None = None
    event_type: str
    role: str
    content: str
    record: dict[str, JsonValue]


def pi_event_source_id(session_id: str, event_id: str, /) -> str:
    """Build the stable identity of one Pi event."""

    identity = f"{PI_EVENT_IDENTITY_PREFIX}{quote(session_id, safe='')}:{quote(event_id, safe='')}"
    if len(identity) > MAX_SOURCE_ID_LENGTH:
        digest = hashlib.sha256(f"{session_id}:{event_id}".encode()).hexdigest()
        identity = f"{PI_EVENT_IDENTITY_PREFIX}{digest}"
    return identity


def parse_pi_session(value: PiSessionInput, /) -> tuple[PiEventInput, ...]:
    """Return the visible events of the selected branch, root first.

    The whole archive is parsed and validated before any event is returned, so a
    broken branch never yields a partial history.
    """

    records, session_id = _read_records(value.content)
    graph: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in records:
        event_id = record.get("id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("every Pi record needs a non-empty id")  # noqa: TRY003
        if event_id in graph:
            raise ValueError("Pi record ids must be unique")  # noqa: TRY003
        parent_id = record.get("parentId")
        if parent_id is not None and parent_id not in graph:
            raise ValueError("a Pi record parent must already exist")  # noqa: TRY003
        graph[event_id] = record
        order.append(event_id)
    leaf_id = order[-1] if value.leaf_id is None else value.leaf_id
    if leaf_id not in graph:
        raise ValueError("the selected Pi branch leaf does not exist")  # noqa: TRY003

    chain: list[str] = []
    cursor: str | None = leaf_id
    while cursor is not None:
        chain.append(cursor)
        parent = graph[cursor].get("parentId")
        cursor = None if parent is None else str(parent)
    chain.reverse()

    events: list[PiEventInput] = []
    for event_id in chain:
        record = graph[event_id]
        visible = _visible_text(record)
        if visible is None:
            continue
        role, content = visible
        parent_id = record.get("parentId")
        events.append(
            PiEventInput(
                session_id=session_id,
                event_id=event_id,
                parent_id=None if parent_id is None else str(parent_id),
                event_type=str(record.get("type") or ""),
                role=role,
                content=f"{role}: {content}",
                record=record,
            )
        )
    return tuple(events)


def _read_records(content: bytes, /) -> tuple[list[dict[str, Any]], str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Pi session must be UTF-8") from error
    if text.startswith("\ufeff"):
        text = text[1:]
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except ValueError as error:
            raise ValueError("Pi session line is not valid JSON") from error
        if not isinstance(record, dict):
            raise ValueError("Pi session line must be a JSON object")  # noqa: TRY003
        records.append(record)
    if not records:
        raise ValueError("Pi session archive is empty")  # noqa: TRY003
    header = records[0]
    session_id = header.get("id")
    if (
        header.get("type") != "session"
        or header.get("version") != PI_SESSION_FORMAT_VERSION
        or not isinstance(session_id, str)
        or not session_id
    ):
        raise ValueError("Pi session header must be type=session version=3 with a non-empty id")  # noqa: TRY003
    return records[1:], session_id


def _visible_text(record: Mapping[str, Any], /) -> tuple[str, str] | None:
    """Return ``(role, body)`` for a visible event, or ``None`` for a control node."""

    record_type = record.get("type")
    if record_type == "message":
        message = record.get("message")
        if not isinstance(message, Mapping):
            return None
        role = str(message.get("role") or "")
        if role == "bashExecution":
            command = str(message.get("command") or "")
            output = str(message.get("output") or "")
            return role, f"$ {command}\n{output}" if output else f"$ {command}"
        if role == "toolResult":
            name = str(message.get("toolName") or "")
            call_id = str(message.get("toolCallId") or "")
            body = "\n".join(_content_parts(message.get("content")))
            return role, f"[tool_result {name} {call_id}] {body}"
        parts = _content_parts(message.get("content"))
        if not parts:
            return None
        return role, "\n".join(parts)
    if record_type == "compaction":
        return "compaction", str(record.get("summary") or "")
    if record_type == "branch_summary":
        return "branch_summary", str(record.get("summary") or "")
    if record_type == "custom_message":
        parts = _content_parts(record.get("content"))
        if not parts:
            return None
        return "custom", "\n".join(parts)
    return None


def _content_parts(content: Any, /) -> list[str]:
    """Render the visible parts of one message body, dropping hidden reasoning."""

    if isinstance(content, str):
        return [content] if content.strip() else []
    if not isinstance(content, list):
        return []
    parts: list[str] = []
    for block in content:
        if not isinstance(block, Mapping):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
        elif block_type == "toolCall":
            name = str(block.get("name") or "")
            call_id = str(block.get("id") or "")
            arguments = block.get("arguments")
            rendered = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            parts.append(f"[tool_call {name} {call_id}] {rendered}")
    return parts


class PiEventSourceAdapter:
    """Resolve and read the runtime's Pi event Source."""

    input_class = PiEventInput
    name = PI_EVENT_SOURCE_NAME
    source_class = PiEventSource

    async def resolve(self, value: PiEventInput, /) -> PiEventSource:
        source_id = pi_event_source_id(value.session_id, value.event_id)
        return PiEventSource(
            name=source_id,
            source_id=source_id,
            materialization=SourceMaterialization.CAPTURED,
            session_id=value.session_id,
            event_id=value.event_id,
            parent_id=value.parent_id,
            event_type=value.event_type,
            role=value.role,
            content=value.content,
            record=value.record,
        )

    async def read(self, source: PiEventSource, /) -> PiEventInput:
        return PiEventInput(
            session_id=source.session_id,
            event_id=source.event_id,
            parent_id=source.parent_id,
            event_type=source.event_type,
            role=source.role,
            content=source.content,
            record=source.record,
        )


class PiEventTextEvidenceProjection:
    """Expose one Pi event as standard textual evidence."""

    name = TEXT_EVIDENCE_PROJECTION_KEY.name
    version = TEXT_EVIDENCE_PROJECTION_KEY.version
    source_class = PiEventSource
    output_class: type[BaseModel] = TextEvidence

    def project(self, source: PiEventSource, /) -> TextEvidence:
        return TextEvidence(
            source_type=PI_EVENT_SOURCE_NAME,
            source_id=source.source_id,
            content=source.content,
            metadata={
                "session_id": source.session_id,
                "event_id": source.event_id,
                "parent_id": source.parent_id,
                "event_type": source.event_type,
                "role": source.role,
            },
        )


PI_EVENT_SOURCE_ADAPTER = PiEventSourceAdapter()
PI_EVENT_SOURCE_DEFINITION: AdapterSourceDefinition[PiEventInput, PiEventSource, PiEventInput] = AdapterSourceDefinition(
    PI_EVENT_SOURCE_ADAPTER,
    version="1",
    projections=(PiEventTextEvidenceProjection(),),
)


class PiSessionConnector:
    """Submit only the selected branch events that were not imported yet."""

    name = PI_SESSION_CONNECTOR_NAME
    version = PI_SESSION_CONNECTOR_VERSION
    source_definitions = frozenset({PI_EVENT_SOURCE_NAME})

    def __init__(self, path: str | Path, leaf_id: str | None = None) -> None:
        self._path = Path(path)
        self._leaf_id = leaf_id

    async def run(self, session: Any, /) -> ConnectorRunCompletion:
        events = parse_pi_session(PiSessionInput(content=self._path.read_bytes(), leaf_id=self._leaf_id))
        imported = _imported_digests(session.checkpoint)
        # Verify every already imported event before submitting anything, so a
        # rewritten history never advances the persisted progress.
        for event in events:
            previous = imported.get(event.event_id)
            if previous is not None and previous != _record_digest(event.record):
                raise ValueError("an imported Pi event was rewritten")  # noqa: TRY003
        for event in events:
            if event.event_id in imported:
                continue
            await session.submit(event.event_id, PI_EVENT_SOURCE_NAME, event)
            imported[event.event_id] = _record_digest(event.record)
        return ConnectorRunCompletion(
            status=ConnectorRunStatus.COMPLETE,
            checkpoint={"events": imported},
        )


def _imported_digests(checkpoint: JsonValue | None, /) -> dict[str, str]:
    if not isinstance(checkpoint, Mapping):
        return {}
    events = checkpoint.get("events")
    if not isinstance(events, Mapping):
        return {}
    return {str(key): str(value) for key, value in events.items()}


def _record_digest(record: Mapping[str, Any], /) -> str:
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "PI_EVENT_SOURCE_DEFINITION",
    "PI_EVENT_SOURCE_NAME",
    "PI_SESSION_CONNECTOR_NAME",
    "PI_SESSION_CONNECTOR_VERSION",
    "PiEventInput",
    "PiEventSource",
    "PiSessionConnector",
    "PiSessionInput",
    "parse_pi_session",
    "pi_event_source_id",
]
