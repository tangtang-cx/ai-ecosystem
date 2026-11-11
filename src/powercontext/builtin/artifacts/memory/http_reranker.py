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

"""HTTP scoring service adapter for Memory reranking.

The service scores coarse search candidates against one query. Its batch limit
may be smaller than the candidate pool, so the adapter splits the pool into
batches, keeps each candidate's original global rank in every request, and
makes one global selection over the complete pool.
"""

from __future__ import annotations

import math

import httpx

from powercontext.builtin.artifacts.memory.models import MemoryHit
from powercontext.builtin.artifacts.memory.reranking import MemoryRerankDecision
from powercontext.builtin.inference import InferenceUsage

HTTP_MEMORY_RERANKER_POLICY_ID = "http-cross-encoder-v1"


class HTTPMemoryReranker:
    """Rank Memory candidates with one HTTP scoring service."""

    policy_id: str

    def __init__(
        self,
        endpoint: str,
        *,
        client: httpx.AsyncClient,
        batch_size: int = 32,
        policy_id: str = HTTP_MEMORY_RERANKER_POLICY_ID,
    ) -> None:
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("reranker endpoint must be a non-empty string")  # noqa: TRY003
        if batch_size < 1:
            raise ValueError("reranker batch size must be positive")  # noqa: TRY003
        self._endpoint = endpoint
        self._client = client
        self._batch_size = batch_size
        self.policy_id = policy_id

    async def rerank(
        self,
        query: str,
        candidates: tuple[MemoryHit, ...],
        limit: int,
        /,
    ) -> MemoryRerankDecision:
        """Score every candidate and select the best original ranks.

        The returned ranks are the candidates' original one-based positions in
        the complete pool, so the caller keeps the identity of every selected
        Memory entry and version.
        """

        if not candidates:
            raise ValueError("rerank requires at least one candidate")  # noqa: TRY003
        if limit < 1 or limit > len(candidates):
            raise ValueError("rerank limit must be between one and the candidate count")  # noqa: TRY003

        scores: dict[int, float] = {}
        requests = 0
        for start in range(0, len(candidates), self._batch_size):
            batch = candidates[start : start + self._batch_size]
            ranks = tuple(range(start + 1, start + len(batch) + 1))
            scores.update(await self._score_batch(query, batch, ranks))
            requests += 1

        selected = tuple(rank for rank, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit])
        return MemoryRerankDecision(
            selected_ranks=selected,
            usage=InferenceUsage(requests=requests),
            discarded_rank_count=len(candidates) - len(selected),
        )

    async def _score_batch(
        self,
        query: str,
        batch: tuple[MemoryHit, ...],
        ranks: tuple[int, ...],
    ) -> dict[int, float]:
        """Score one batch and return its scores keyed by the original rank."""

        payload = {
            "query": query,
            "candidates": [
                {"rank": rank, "text": candidate.text} for rank, candidate in zip(ranks, batch, strict=True)
            ],
        }
        response = await self._client.post(self._endpoint, json=payload)
        response.raise_for_status()
        return _parse_scores(response, set(ranks))


def _parse_scores(response: httpx.Response, expected_ranks: set[int]) -> dict[int, float]:
    """Validate one service response against exactly the ranks that were sent."""

    try:
        body = response.json()
    except ValueError as error:
        raise ValueError("reranker response is not valid JSON") from error
    if not isinstance(body, dict) or set(body) != {"scores"}:
        raise ValueError("reranker response must contain exactly the scores field")  # noqa: TRY003
    records = body["scores"]
    if not isinstance(records, list):
        raise ValueError("reranker scores must be a list")  # noqa: TRY003

    scores: dict[int, float] = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"rank", "score"}:
            raise ValueError("reranker score records must contain exactly rank and score")  # noqa: TRY003
        rank = record["rank"]
        if type(rank) is not int:
            raise ValueError("reranker ranks must be integers")  # noqa: TRY003
        score = record["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("reranker scores must be numbers")  # noqa: TRY003
        if not math.isfinite(float(score)):
            raise ValueError("reranker scores must be finite")  # noqa: TRY003
        if rank not in expected_ranks:
            raise ValueError("reranker ranks must belong to the requested batch")  # noqa: TRY003
        if rank in scores:
            raise ValueError("reranker ranks must not repeat")  # noqa: TRY003
        scores[rank] = float(score)
    if set(scores) != expected_ranks:
        raise ValueError("reranker response must cover every requested rank")  # noqa: TRY003
    return scores


__all__ = ["HTTP_MEMORY_RERANKER_POLICY_ID", "HTTPMemoryReranker"]
