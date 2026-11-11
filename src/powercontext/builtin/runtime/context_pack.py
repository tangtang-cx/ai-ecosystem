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

"""Wire protocol for incremental Context Pack transmission.

A Context Pack carries the exact bytes of one prepared context as an ordered
list of chunks. The first transmission sends the whole pack; every later turn
sends a delta that keeps a prefix of the previous pack and carries the
remaining target chunks. A receiver rebuilds the target pack from the base pack
and the delta alone, so no process state is shared between sender and receiver.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from typing import Any

CONTEXT_PACK_SCHEMA = "powercontext.context-pack.v1"
CONTEXT_PACK_DELTA_SCHEMA = "powercontext.context-pack-delta.v1"
DEFAULT_CHUNK_BYTES = 512

_PACK_FIELDS = frozenset({"schema", "items", "digest", "byte_count"})
_DELTA_FIELDS = frozenset({"schema", "base_digest", "target_digest", "prefix_items", "appended"})


class ContextPackError(Exception):
    """Raised when a Context Pack or delta violates the wire contract."""


@dataclass(frozen=True, slots=True)
class ContextPack:
    """One complete Context Pack: ordered chunks plus their digest."""

    items: tuple[bytes, ...]
    digest: str

    @classmethod
    def build(cls, items: tuple[bytes, ...]) -> ContextPack:
        """Build one pack from already chunked content."""

        normalized = _normalize_items(items)
        return cls(items=normalized, digest=_pack_digest(normalized))

    @classmethod
    def from_content(cls, content: str, *, chunk_bytes: int = DEFAULT_CHUNK_BYTES) -> ContextPack:
        """Split one text into deterministic chunks that keep the original bytes."""

        return cls.build(_chunk_text(content, chunk_bytes))

    @property
    def byte_count(self) -> int:
        """The exact wire size of this pack, including its own byte-count field."""

        return len(self.to_bytes())

    def to_bytes(self) -> bytes:
        """Serialize the pack with the canonical JSON encoding."""

        payload: dict[str, Any] = {
            "schema": CONTEXT_PACK_SCHEMA,
            "items": [_encode_item(item) for item in self.items],
            "digest": self.digest,
            "byte_count": 0,
        }
        size = len(_canonical_json(payload))
        for _ in range(8):
            payload["byte_count"] = size
            actual = len(_canonical_json(payload))
            if actual == size:
                break
            size = actual
        encoded = _canonical_json(payload)
        if len(encoded) != payload["byte_count"]:
            raise ContextPackError("context pack byte count does not converge")  # noqa: TRY003
        return encoded

    @classmethod
    def from_bytes(cls, data: bytes) -> ContextPack:
        """Decode and verify one pack received from the wire."""

        payload = _decode_object(data, _PACK_FIELDS, "context pack")
        if payload["schema"] != CONTEXT_PACK_SCHEMA:
            raise ContextPackError("context pack schema is not supported")  # noqa: TRY003
        items = _decode_items(payload["items"], "context pack")
        digest = payload["digest"]
        if not isinstance(digest, str) or _pack_digest(items) != digest:
            raise ContextPackError("context pack digest does not match its content")  # noqa: TRY003
        byte_count = payload["byte_count"]
        if type(byte_count) is not int or byte_count < 0:
            raise ContextPackError("context pack byte count must be a non-negative integer")  # noqa: TRY003
        pack = cls(items=items, digest=digest)
        if pack.byte_count != byte_count:
            raise ContextPackError("context pack byte count does not match its encoding")  # noqa: TRY003
        return pack


@dataclass(frozen=True, slots=True)
class ContextPackDelta:
    """One incremental update that turns a base pack into a target pack."""

    base_digest: str
    target_digest: str
    prefix_items: int
    appended: tuple[bytes, ...]

    @classmethod
    def between(cls, base: ContextPack, target: ContextPack) -> ContextPackDelta:
        """Keep the shared leading chunks of the base and carry the rest of the target."""

        prefix = 0
        for base_item, target_item in zip(base.items, target.items, strict=False):
            if base_item != target_item:
                break
            prefix += 1
        return cls(
            base_digest=base.digest,
            target_digest=target.digest,
            prefix_items=prefix,
            appended=target.items[prefix:],
        )

    @property
    def byte_count(self) -> int:
        """The exact wire size of this delta."""

        return len(self.to_bytes())

    def to_bytes(self) -> bytes:
        """Serialize the delta with the canonical JSON encoding."""

        payload: dict[str, Any] = {
            "schema": CONTEXT_PACK_DELTA_SCHEMA,
            "base_digest": self.base_digest,
            "target_digest": self.target_digest,
            "prefix_items": self.prefix_items,
            "appended": [_encode_item(item) for item in self.appended],
        }
        return _canonical_json(payload)

    @classmethod
    def from_bytes(cls, data: bytes) -> ContextPackDelta:
        """Decode and verify one delta received from the wire."""

        payload = _decode_object(data, _DELTA_FIELDS, "context pack delta")
        if payload["schema"] != CONTEXT_PACK_DELTA_SCHEMA:
            raise ContextPackError("context pack delta schema is not supported")  # noqa: TRY003
        prefix_items = payload["prefix_items"]
        if type(prefix_items) is not int or prefix_items < 0:
            raise ContextPackError("context pack delta prefix must be a non-negative integer")  # noqa: TRY003
        base_digest = payload["base_digest"]
        target_digest = payload["target_digest"]
        if not isinstance(base_digest, str) or not isinstance(target_digest, str):
            raise ContextPackError("context pack delta digests must be strings")  # noqa: TRY003
        appended = _decode_items(payload["appended"], "context pack delta")
        return cls(
            base_digest=base_digest,
            target_digest=target_digest,
            prefix_items=prefix_items,
            appended=appended,
        )


def apply_context_pack_delta(base: ContextPack, delta: ContextPackDelta) -> ContextPack:
    """Rebuild the target pack from a base pack and one delta."""

    if delta.base_digest != base.digest:
        raise ContextPackError("context pack delta does not match the base pack")  # noqa: TRY003
    if delta.prefix_items > len(base.items):
        raise ContextPackError("context pack delta prefix exceeds the base pack")  # noqa: TRY003
    target = ContextPack.build(base.items[: delta.prefix_items] + delta.appended)
    if target.digest != delta.target_digest:
        raise ContextPackError("context pack delta does not reproduce the target pack")  # noqa: TRY003
    return target


def _canonical_json(payload: dict[str, Any]) -> bytes:
    """Encode one wire payload with sorted keys and no extra whitespace."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pack_digest(items: tuple[bytes, ...]) -> str:
    """Digest the schema and the encoded items of one pack."""

    canonical = _canonical_json({
        "schema": CONTEXT_PACK_SCHEMA,
        "items": [_encode_item(item) for item in items],
    })
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _encode_item(item: bytes) -> str:
    """Encode one chunk as a standard Base64 string."""

    return base64.b64encode(item).decode("ascii")


def _normalize_items(items: tuple[bytes, ...]) -> tuple[bytes, ...]:
    """Accept only byte chunks and keep their order."""

    normalized: list[bytes] = []
    for item in items:
        if not isinstance(item, bytes):
            raise ContextPackError("context pack items must be bytes")  # noqa: TRY003
        normalized.append(item)
    return tuple(normalized)


def _decode_object(data: bytes, expected: frozenset[str], label: str) -> dict[str, Any]:
    """Decode one wire object and require exactly the contracted fields."""

    try:
        payload = json.loads(data.decode("utf-8"))
    except ValueError as error:
        raise ContextPackError(f"{label} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise ContextPackError(f"{label} must be a JSON object")  # noqa: TRY003
    if set(payload) != expected:
        raise ContextPackError(f"{label} must contain exactly the fields {sorted(expected)}")  # noqa: TRY003
    return payload


def _decode_items(values: Any, label: str) -> tuple[bytes, ...]:
    """Decode the Base64 chunk list of one wire object."""

    if not isinstance(values, list):
        raise ContextPackError(f"{label} items must be a list")  # noqa: TRY003
    items: list[bytes] = []
    for value in values:
        if not isinstance(value, str):
            raise ContextPackError(f"{label} items must be Base64 strings")  # noqa: TRY003
        try:
            items.append(base64.b64decode(value, validate=True))
        except (binascii.Error, ValueError) as error:
            raise ContextPackError(f"{label} items must be valid Base64") from error
    return tuple(items)


def _chunk_text(content: str, chunk_bytes: int) -> tuple[bytes, ...]:
    """Split text into chunks that keep the original bytes and stay within the limit."""

    if type(chunk_bytes) is not int or chunk_bytes < 1:
        raise ContextPackError("context pack chunk size must be a positive integer")  # noqa: TRY003
    if not content:
        return ()
    encoded = content.encode("utf-8")
    items: list[bytes] = []
    current = bytearray()
    position = 0
    total = len(encoded)
    while position < total:
        newline = encoded.find(b"\n", position)
        line_end = total if newline < 0 else newline + 1
        line = encoded[position:line_end]
        while line:
            room = chunk_bytes - len(current)
            if room <= 0:
                items.append(bytes(current))
                current = bytearray()
                continue
            piece, line = _take_utf8_prefix(line, room)
            if piece is None:
                if current:
                    items.append(bytes(current))
                    current = bytearray()
                    continue
                raise ContextPackError("context pack chunk size cannot hold one UTF-8 character")  # noqa: TRY003
            current.extend(piece)
        position = line_end
    if current:
        items.append(bytes(current))
    return tuple(items)


def _take_utf8_prefix(data: bytes, room: int) -> tuple[bytes | None, bytes]:
    """Split off the longest valid UTF-8 prefix that fits into ``room`` bytes."""

    take = min(room, len(data))
    while take > 0:
        try:
            data[:take].decode("utf-8")
        except UnicodeDecodeError:
            take -= 1
            continue
        return data[:take], data[take:]
    return None, data


__all__ = [
    "CONTEXT_PACK_DELTA_SCHEMA",
    "CONTEXT_PACK_SCHEMA",
    "DEFAULT_CHUNK_BYTES",
    "ContextPack",
    "ContextPackDelta",
    "ContextPackError",
    "apply_context_pack_delta",
]
