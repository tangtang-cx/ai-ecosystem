"""Real seekdb storage layer: HNSW vector index + IK fulltext index + RRF fusion.

Everything happens **inside the seekdb kernel**:

* the collection is a real table with ``VECTOR(512)`` + ``FULLTEXT INDEX ... PARSER ik``
  + ``VECTOR INDEX ... type=hnsw, lib=vsag``;
* the hybrid plan is produced by ``DBMS_HYBRID_SEARCH.GET_SQL`` and executed by seekdb;
* the two recall branches (vector / fulltext) are fused by seekdb's RRF ranker.

Two deployment modes:

* ``embedded`` (default) -- ``pylibseekdb.open(path)`` starts a local seekdb kernel;
* ``server``            -- connect to a running seekdb / OceanBase instance
  (``SEEKDB_HOST`` / ``SEEKDB_PORT`` / ``SEEKDB_USER`` / ``SEEKDB_PASSWORD``).

The DDL and the ``@search_parm`` contract are the ones already verified against a
real seekdb kernel in ``stepfun/tools/verify_seekdb_contract.py``.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

TABLE = "dify_knowledge_base"
EMBEDDING_DIM = 512

CREATE_TABLE = f"""CREATE TABLE IF NOT EXISTS `{TABLE}` (
  id VARBINARY(512) PRIMARY KEY NOT NULL,
  document STRING,
  embedding VECTOR({EMBEDDING_DIM}),
  metadata JSON,
  FULLTEXT INDEX idx_fts (document) WITH PARSER ik PARSER_PROPERTIES=(ik_mode='smart'),
  VECTOR INDEX idx_vec (embedding) WITH(distance=cosine, type=hnsw, lib=vsag, m=16, ef_construction=200, ef_search=64)
) ORGANIZATION = HEAP"""


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{float(v):.6f}" for v in values) + "]"


class SeekdbStore:
    """Thin adapter over the seekdb kernel (embedded or server mode)."""

    def __init__(self, db_dir: str | Path | None = None) -> None:
        self.mode = "embedded"
        self.db_dir = Path(db_dir or os.environ.get("SEEKDB_PATH", "./.data/dify-seekdb"))
        self._instance = None
        self._connection = None
        self._cursor = None

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def open(self, reset: bool = False) -> None:
        host = os.environ.get("SEEKDB_HOST")
        if host:
            self.mode = "server"
            import pylibseekdb

            self._instance = pylibseekdb.connect(
                host,
                int(os.environ.get("SEEKDB_PORT", "2881")),
                os.environ.get("SEEKDB_USER", "root"),
                os.environ.get("SEEKDB_PASSWORD", ""),
                os.environ.get("SEEKDB_DATABASE", "test"),
            )
        else:
            self.mode = "embedded"
            import pylibseekdb

            if reset and self.db_dir.exists():
                shutil.rmtree(self.db_dir, ignore_errors=True)
            self.db_dir.mkdir(parents=True, exist_ok=True)
            self._instance = pylibseekdb.open(str(self.db_dir))
        self._connection = self._instance.connect(os.environ.get("SEEKDB_DATABASE", "test"))
        self._cursor = self._connection.cursor()
        if reset:
            try:
                self._cursor.execute(f"DROP TABLE IF EXISTS `{TABLE}`")
            except Exception:
                pass
        self._cursor.execute(CREATE_TABLE)

    def close(self) -> None:
        try:
            if self._connection is not None:
                self._connection.close()
            if self._instance is not None:
                self._instance.close()
        finally:
            self._cursor = None
            self._connection = None
            self._instance = None

    # ------------------------------------------------------------------ #
    # writes
    # ------------------------------------------------------------------ #
    def upsert(self, rows: list[dict[str, Any]]) -> int:
        """rows: [{id, text, metadata, embedding}]"""
        if not rows:
            return 0
        values = []
        for row in rows:
            metadata = json.dumps(row.get("metadata", {}), ensure_ascii=False)
            values.append(
                "(CAST({} AS BINARY), {}, CAST({} AS JSON), {})".format(
                    sql_str(str(row["id"])),
                    sql_str(row["text"]),
                    sql_str(metadata),
                    sql_vector(row["embedding"]),
                )
            )
        statement = (
            f"INSERT INTO `{TABLE}` (id, document, metadata, embedding) VALUES " + ", ".join(values)
        )
        self._cursor.execute(statement)
        self.refresh()
        return len(rows)

    def refresh(self) -> None:
        """Flush pending index builds so freshly written rows become searchable."""
        try:
            self._cursor.execute("CALL dbms_index_manager.refresh();")
        except Exception:
            # kernel dependent: some builds flush automatically
            pass

    def count(self) -> int:
        self._cursor.execute(f"SELECT COUNT(*) FROM `{TABLE}`")
        return int(self._cursor.fetchone()[0])

    # ------------------------------------------------------------------ #
    # reads
    # ------------------------------------------------------------------ #
    def _hybrid_sql(self, parm: dict[str, Any]) -> str:
        payload = json.dumps(parm, ensure_ascii=False)
        self._cursor.execute(f"SET @search_parm = {sql_str(payload)}")
        self._cursor.execute(
            f"SELECT DBMS_HYBRID_SEARCH.GET_SQL('{TABLE}', @search_parm) as query_sql FROM dual"
        )
        plan = str(self._cursor.fetchall()[0][0]).strip().strip("'\"")
        return plan

    def search(
        self,
        query: str,
        embedding: list[float] | None = None,
        top_k: int = 5,
        mode: str = "hybrid",
    ) -> list[dict[str, Any]]:
        """Run the hybrid (or single-branch) search inside seekdb.

        mode: ``hybrid`` (vector + fulltext, RRF), ``vector``, ``fulltext``.
        """
        size = max(int(top_k), 1)
        candidate = max(size * 3, 12)
        parm: dict[str, Any] = {"size": size}

        if mode in {"hybrid", "fulltext"} and query.strip():
            parm["query"] = {"query_string": {"fields": ["document"], "query": query}}
        if mode in {"hybrid", "vector"} and embedding:
            parm["knn"] = {"field": "embedding", "k": candidate, "query_vector": embedding}
        if mode == "hybrid":
            parm["rank"] = {"rrf": {}}

        plan = self._hybrid_sql(parm)
        self._cursor.execute(plan)
        rows = self._cursor.fetchall()

        # The generated plan selects: id, document, embedding, metadata, _score
        hits: list[dict[str, Any]] = []
        for row in rows:
            identifier = row[0]
            document = row[1] if len(row) > 1 else ""
            metadata = row[3] if len(row) > 3 else {}
            score = row[4] if len(row) > 4 else None
            if isinstance(metadata, (bytes, bytearray)):
                metadata = metadata.decode("utf-8", "replace")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            hits.append(
                {
                    "id": identifier.decode("utf-8", "replace") if isinstance(identifier, bytes) else str(identifier),
                    "text": document,
                    "title": metadata.get("title", "未命名片段"),
                    "source": metadata.get("source", ""),
                    "score": float(score) if isinstance(score, (int, float)) else None,
                }
            )
        return hits

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "mode": self.mode,
            "table": TABLE,
            "chunks": self.count(),
            "embedding_dim": EMBEDDING_DIM,
        }


def chunk_text(text: str, size: int = 700, overlap: int = 80) -> list[str]:
    """Split markdown into paragraph-aware chunks."""
    paragraphs = [block.strip() for block in text.split("\n\n") if block.strip()]
    chunks: list[str] = []
    current = ""
    for block in paragraphs:
        if len(current) + len(block) + 2 <= size or not current:
            current = f"{current}\n\n{block}".strip() if current else block
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{block}".strip() if tail else block
    if current:
        chunks.append(current)
    return chunks
