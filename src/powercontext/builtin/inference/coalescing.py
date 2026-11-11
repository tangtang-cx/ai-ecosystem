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

"""Cross-call request coalescing and vector caching for embedding models.

One wrapper serves every scope of one Runtime. Identical texts that arrive
while a request is still running share that request, successful vectors stay
available for later calls within a bounded LRU capacity, and a cancelled
caller never cancels the work other callers are waiting for.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from powercontext.builtin.inference.models import EmbeddingResult, InferenceUsage

EmbedCall = Callable[[tuple[str, ...]], Awaitable[EmbeddingResult]]


@dataclass(slots=True)
class _Batch:
    """One base request shared by every caller that needs its texts."""

    texts: tuple[str, ...]
    task: asyncio.Task[dict[str, tuple[float, ...]]] | None = None
    usage: InferenceUsage = field(default_factory=lambda: InferenceUsage(requests=0))


class _Channel:
    """Hold the cache and the in-flight requests of one embedding channel.

    Documents and queries keep separate channels so a deployment that embeds
    them differently never serves one from the other's cache.
    """

    def __init__(self, max_batch_size: int, coalesce_seconds: float, cache_size: int) -> None:
        self._max_batch_size = max_batch_size
        self._coalesce_seconds = coalesce_seconds
        self._cache_size = cache_size
        self._cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self._pending: dict[str, _Batch] = {}

    async def embed(self, texts: tuple[str, ...], call: EmbedCall, /) -> EmbeddingResult:
        """Resolve one ordered batch of texts, sharing and caching the work."""

        if not texts:
            return EmbeddingResult(vectors=(), usage=InferenceUsage(requests=0))
        unique = tuple(dict.fromkeys(texts))
        resolved: dict[str, tuple[float, ...]] = {}
        batches: list[_Batch] = []
        shared: list[_Batch] = []
        fresh: list[str] = []
        for text in unique:
            cached = self._cache_get(text)
            if cached is not None:
                resolved[text] = cached
                continue
            batch = self._pending.get(text)
            if batch is not None:
                if batch not in shared:
                    shared.append(batch)
                continue
            fresh.append(text)
        if fresh:
            batches.extend(self._register(fresh, call))
        batches.extend(shared)
        if batches:
            mappings = await asyncio.gather(*(asyncio.shield(batch.task) for batch in batches))
            for mapping in mappings:
                resolved.update(mapping)
        return EmbeddingResult(
            vectors=tuple(resolved[text] for text in texts),
            usage=_usage_of(batches),
        )

    def _register(self, texts: list[str], call: EmbedCall, /) -> list[_Batch]:
        """Claim the given texts and start one base request per bounded batch."""

        batches: list[_Batch] = []
        for start in range(0, len(texts), self._max_batch_size):
            chunk = tuple(texts[start : start + self._max_batch_size])
            batch = _Batch(texts=chunk)
            for text in chunk:
                self._pending[text] = batch
            batch.task = asyncio.create_task(self._execute(batch, call))
            batches.append(batch)
        return batches

    async def _execute(self, batch: _Batch, call: EmbedCall, /) -> dict[str, tuple[float, ...]]:
        """Run one base request and publish its vectors to the cache."""

        try:
            if self._coalesce_seconds > 0:
                await asyncio.sleep(self._coalesce_seconds)
            result = await call(batch.texts)
            vectors = tuple(result.vectors)
            if len(vectors) != len(batch.texts):
                raise ValueError("embedding model returned a different number of vectors than requested texts")  # noqa: TRY003
            mapping = dict(zip(batch.texts, vectors, strict=True))
            batch.usage = result.usage
            self._cache_store(mapping)
            return mapping
        finally:
            for text in batch.texts:
                if self._pending.get(text) is batch:
                    del self._pending[text]

    def _cache_get(self, text: str, /) -> tuple[float, ...] | None:
        if self._cache_size < 1:
            return None
        vector = self._cache.get(text)
        if vector is None:
            return None
        self._cache.move_to_end(text)
        return vector

    def _cache_store(self, mapping: dict[str, tuple[float, ...]], /) -> None:
        if self._cache_size < 1:
            return
        for text, vector in mapping.items():
            self._cache[text] = vector
            self._cache.move_to_end(text)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)


class CoalescingEmbeddingModel:
    """Share embedding work across concurrent calls and cache successful vectors."""

    def __init__(
        self,
        model: Any,
        *,
        max_batch_size: int = 64,
        coalesce_ms: float = 5.0,
        cache_size: int = 1024,
    ) -> None:
        if type(max_batch_size) is not int or max_batch_size < 1:
            raise ValueError("max_batch_size must be a positive integer")  # noqa: TRY003
        if isinstance(coalesce_ms, bool) or not isinstance(coalesce_ms, (int, float)):
            raise ValueError("coalesce_ms must be a number")  # noqa: TRY003
        if coalesce_ms < 0:
            raise ValueError("coalesce_ms must not be negative")  # noqa: TRY003
        if type(cache_size) is not int or cache_size < 0:
            raise ValueError("cache_size must not be a negative integer")  # noqa: TRY003
        self._model = model
        self._documents = _Channel(max_batch_size, coalesce_ms / 1000, cache_size)
        self._queries = _Channel(max_batch_size, coalesce_ms / 1000, cache_size)

    @property
    def profile(self) -> Any:
        """Expose the wrapped deployment profile."""

        return self._model.profile

    async def embed(self, texts: tuple[str, ...], /) -> EmbeddingResult:
        """Embed an ordered text batch, sharing work and caching the result."""

        return await self._documents.embed(texts, self._model.embed)

    async def embed_query(self, texts: tuple[str, ...], /) -> EmbeddingResult:
        """Embed retrieval queries, keeping them apart from document vectors."""

        embed_query = getattr(self._model, "embed_query", None)
        if embed_query is None:
            return await self._documents.embed(texts, self._model.embed)
        return await self._queries.embed(texts, embed_query)


def _usage_of(batches: list[_Batch], /) -> InferenceUsage:
    """Sum the provider usage of every batch this call waited for, once each."""

    requests = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    for batch in batches:
        requests += batch.usage.requests or 0
        if batch.usage.input_tokens is not None:
            input_tokens = (input_tokens or 0) + batch.usage.input_tokens
        if batch.usage.output_tokens is not None:
            output_tokens = (output_tokens or 0) + batch.usage.output_tokens
    return InferenceUsage(requests=requests, input_tokens=input_tokens, output_tokens=output_tokens)


__all__ = ["CoalescingEmbeddingModel"]
