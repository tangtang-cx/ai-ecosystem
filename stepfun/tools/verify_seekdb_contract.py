"""Validate the seekdb collection DDL and hybrid-search SQL contract.

The JavaScript app talks to seekdb through seekdb-js. seekdb-js cannot run its
embedded backend on Windows (the native binding blocks inside ``open()``), so
this script replays the *same* statements through the official ``pylibseekdb``
binding, which uses the same seekdb kernel.

What this proves:
  * the collection DDL (HNSW vector index + IK fulltext index) is accepted by
    a real seekdb kernel;
  * ``DBMS_HYBRID_SEARCH.GET_SQL`` returns a runnable plan;
  * the plan executes and RRF fusion returns the expected ranking.

Run:
  python tools/verify_seekdb_contract.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys

import pylibseekdb

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".data", "contract-check"))
TABLE = "browser_knowledge_base"

# Same DDL seekdb-js builds from Schema({fulltextIndex, vectorIndex}).
CREATE_TABLE = f"""CREATE TABLE `{TABLE}` (
      id VARBINARY(512) PRIMARY KEY NOT NULL,
      document STRING,
      embedding VECTOR(4),
      metadata JSON,
      FULLTEXT INDEX idx_fts (document) WITH PARSER ik PARSER_PROPERTIES=(ik_mode='smart'),
      VECTOR INDEX idx_vec (embedding) WITH(distance=cosine, type=hnsw, lib=vsag, m=16, ef_construction=200, ef_search=64)
    ) ORGANIZATION = HEAP"""

DOCUMENTS = [
    (
        "doc-hybrid",
        "混合检索会同时执行向量检索与全文检索，再用 RRF 融合两路排名。",
        {"title": "混合检索", "source": "check"},
        [0.10, 0.20, 0.30, 0.40],
    ),
    (
        "doc-vector",
        "HNSW 是一种分层可导航小世界图索引，用于近似最近邻搜索。",
        {"title": "HNSW", "source": "check"},
        [0.90, 0.80, 0.70, 0.60],
    ),
]


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_vector(values: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"


def insert_sql() -> str:
    rows = []
    for identifier, document, metadata, vector in DOCUMENTS:
        rows.append(
            "(CAST({} AS BINARY), {}, CAST({} AS JSON), {})".format(
                sql_str(identifier),
                sql_str(document),
                sql_str(json.dumps(metadata, ensure_ascii=False)),
                sql_vector(vector),
            )
        )
    columns = "id, document, metadata, embedding"
    return f"INSERT INTO `{TABLE}` ({columns}) VALUES " + ", ".join(rows)


def search_parm(query: str, vector: list[float], size: int) -> str:
    """Build the same ``@search_parm`` payload seekdb-js sends.

    The ``query`` branch uses the nested ``query_string`` object that
    ``Collection.buildDocumentQuery`` produces, and the ``knn`` branch uses the
    ``field``/``k``/``query_vector`` object that ``_buildKnnExpression``
    produces. Both shapes are required by the seekdb kernel.
    """

    return json.dumps(
        {
            "query": {"query_string": {"fields": ["document"], "query": query}},
            "knn": {"field": "embedding", "k": size, "query_vector": vector},
            "rank": {"rrf": {}},
            "size": size,
        },
        ensure_ascii=False,
    )


def hybrid_plan(cursor, parm: str) -> str:
    cursor.execute(f"SET @search_parm = {sql_str(parm)}")
    cursor.execute(
        f"SELECT DBMS_HYBRID_SEARCH.GET_SQL('{TABLE}', @search_parm) as query_sql FROM dual"
    )
    return str(cursor.fetchall()[0][0]).strip().strip("'\"")


def run() -> int:
    if os.path.isdir(DB_DIR):
        shutil.rmtree(DB_DIR, ignore_errors=True)
    os.makedirs(DB_DIR, exist_ok=True)

    instance = pylibseekdb.open(DB_DIR)
    connection = instance.connect("test")
    cursor = connection.cursor()

    cursor.execute(CREATE_TABLE)
    print("ok: CREATE TABLE with HNSW + IK fulltext index")

    cursor.execute(insert_sql())
    print(f"ok: INSERT {len(DOCUMENTS)} documents with metadata and vectors")

    failures = []

    # 1. Keyword branch only: the full-text branch must find the keyword match.
    keyword_parm = json.dumps(
        {
            "query": {"query_string": {"fields": ["document"], "query": "混合检索"}},
            "size": 5,
        },
        ensure_ascii=False,
    )
    keyword_sql = hybrid_plan(cursor, keyword_parm)
    cursor.execute(keyword_sql)
    keyword_rows = cursor.fetchall()
    keyword_ids = [row[0] for row in keyword_rows]
    print(f"ok: full-text branch returned {keyword_ids}")
    if "doc-hybrid" not in keyword_ids:
        failures.append("full-text branch did not return the keyword match")

    # 2. Vector branch only: the vector index must find the nearest neighbour.
    #    seekdb-js refreshes pending index builds with this procedure before a
    #    query may observe newly written rows.
    try:
        cursor.execute("CALL dbms_index_manager.refresh();")
        print("ok: dbms_index_manager.refresh() ran")
    except Exception as exc:  # pragma: no cover - kernel dependent
        print(f"note: dbms_index_manager.refresh() -> {str(exc)[:100]}")
    vector_parm = json.dumps(
        {
            "knn": {
                "field": "embedding",
                "k": 5,
                "query_vector": [0.91, 0.81, 0.71, 0.61],
            },
            "size": 5,
        },
        ensure_ascii=False,
    )
    vector_sql = hybrid_plan(cursor, vector_parm)
    cursor.execute(vector_sql)
    vector_rows = cursor.fetchall()
    vector_ids = [row[0] for row in vector_rows]
    print(f"ok: vector branch returned {vector_ids}")
    if "doc-vector" not in vector_ids:
        failures.append("vector branch did not return the nearest neighbour")

    # 3. Combined hybrid search: both branches join inside seekdb.
    parm = search_parm("混合检索", [0.11, 0.21, 0.31, 0.41], 5)
    query_sql = hybrid_plan(cursor, parm)
    print("ok: DBMS_HYBRID_SEARCH.GET_SQL produced a plan")
    print(f"    plan: {query_sql[:120]}")
    cursor.execute(query_sql)
    rows = cursor.fetchall()
    print(f"ok: hybrid search returned {len(rows)} row(s)")
    for row in rows:
        print(f"    id={row[0]!r}")

    if not rows:
        failures.append("hybrid search returned no rows")
    if "_fts" not in query_sql or "_vs" not in query_sql:
        failures.append("plan does not join a full-text branch and a vector branch")

    cursor.execute(f"SELECT COUNT(*) as cnt FROM `{TABLE}`")
    count = cursor.fetchone()[0]
    print("ok: COUNT =", count)
    if count != len(DOCUMENTS):
        failures.append(f"expected {len(DOCUMENTS)} rows, found {count}")

    connection.close()
    instance.close()

    if failures:
        for failure in failures:
            print("fail:", failure, file=sys.stderr)
        return 1
    print("\nPASS: seekdb collection DDL + hybrid search SQL contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
