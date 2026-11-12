#!/usr/bin/env python3
"""Deterministic SQL rule scanner used by the oceanbase-sql-reviewer Skill.

Standard library only, so it runs anywhere:

    python scripts/review_rules.py "SELECT * FROM t WHERE DATE(c) = '2026-01-01' LIMIT 20, 200000;"

Exit code 0 = no blocking issue, 1 = at least one blocking issue.
"""

from __future__ import annotations

import json
import re
import sys

LEVEL_LABEL = {"error": "BLOCK", "warn": "WARN", "info": "INFO"}

RULES = [
    ("OB-001", "error", "UPDATE / DELETE without WHERE",
     r"\b(update|delete\s+from)\b(?![\s\S]{0,400}?\bwhere\b)",
     "the statement touches every row of the table",
     "add a WHERE clause; in production, SELECT the affected rows first inside the same transaction"),
    ("OB-002", "error", "JOIN without ON/USING",
     r"\bjoin\b(?![^;]{0,400}?\b(on|using)\b)",
     "a JOIN without an ON/USING clause produces a cartesian product",
     "add the join condition and make sure both sides have the same type"),
    ("OB-003", "error", "CREATE TABLE without PRIMARY KEY",
     r"\bcreate\s+(temporary\s+)?table\b(?![^;]{0,2000}?\bprimary\s+key\b)",
     "the table has no primary key",
     "add a PRIMARY KEY (prefer a monotonic BIGINT over a random UUID)"),
    ("OB-004", "warn", "SELECT *",
     r"\bselect\s+\*",
     "SELECT * reads every column and blocks covering indexes",
     "list the columns explicitly"),
    ("OB-005", "warn", "LIKE with a leading wildcard",
     r"\blike\s+'%",
     "a leading wildcard cannot use an index",
     "use a prefix match (LIKE 'x%') or a fulltext index"),
    ("OB-006", "warn", "indexed column wrapped in a function",
     r"\b(where|and|or)\b[^;\n]{0,400}?\b(year|month|day|date|date_format|substring|left|right|lower|upper|concat)\s*\(\s*[a-z_][a-z0-9_]*\s*\)",
     "a function on the column makes the index unusable",
     "rewrite as a range predicate or add a functional/generated column index"),
    ("OB-007", "warn", "deep pagination OFFSET",
     r"\blimit\s+\d+\s*,\s*(\d{4,})|\boffset\s+(\d{4,})\b",
     "a large OFFSET makes the server scan and discard all skipped rows",
     "use keyset pagination: WHERE id > :last_id ORDER BY id LIMIT n"),
    ("OB-008", "warn", "NOT IN / != with nullable columns",
     r"\bnot\s+in\s*\(|\b(!=|<>)\b",
     "NOT IN returns an empty set as soon as a NULL shows up",
     "use NOT EXISTS and declare the column NOT NULL"),
    ("OB-009", "warn", "very long IN list",
     r"\bin\s*\([^()]*\)",
     "a long IN list slows down parsing and bloats the plan",
     "join a temporary table or batch the statements"),
    ("OB-010", "warn", "SELECT ... FOR UPDATE without WHERE",
     r"\bfor\s+update\b(?![\s\S]{0,400}?\bwhere\b)",
     "a FOR UPDATE without WHERE locks the whole table",
     "narrow the lock with a WHERE clause and keep the transaction short"),
    ("OB-011", "info", "UNION de-duplicates",
     r"\bunion\b(?!\s+all\b)",
     "UNION sorts or hashes to remove duplicates",
     "use UNION ALL when duplicates do not matter"),
    ("OB-012", "info", "TRUNCATE used to clear a table",
     r"\btruncate\s+(table\s+)?",
     "TRUNCATE is DDL: it cannot be rolled back and resets AUTO_INCREMENT",
     "use DELETE when you need a rollback"),
    ("OB-013", "info", "no execution plan attached",
     r"^\s*(select|with)\b",
     "the statement was not verified against an execution plan",
     "run EXPLAIN / EXPLAIN FORMAT=JSON and check the index and scanned rows"),
    ("OB-014", "info", "possible implicit type conversion",
     r"\b([a-z_][a-z0-9_]*)\s*=\s*(\d{1,18})\b",
     "comparing a numeric literal with a string column forces an implicit cast and disables the index",
     "make the literal type match the column type"),
    ("OB-015", "info", "COUNT(1) instead of COUNT(*)",
     r"\bcount\s*\(\s*1\s*\)",
     "modern MySQL protocol / OceanBase optimise COUNT(*) as well",
     "write COUNT(*) for clarity"),
]

_COMMENT_RE = re.compile(r"(--[^\n]*|/\*[\s\S]*?\*/)")
_WS_RE = re.compile(r"\s+")


def normalize(sql: str) -> str:
    return _WS_RE.sub(" ", _COMMENT_RE.sub(" ", sql)).strip()


def long_in_list(sql: str) -> bool:
    for match in re.finditer(r"\bin\s*\(([^()]*)\)", sql, re.IGNORECASE):
        if match.group(1).count(",") + 1 > 50:
            return True
    return False


def analyze(sql: str) -> list[dict]:
    cleaned = normalize(sql)
    findings = []
    for rule_id, level, title, pattern, message, suggestion in RULES:
        if rule_id == "OB-009":
            if not long_in_list(cleaned):
                continue
            snippet = ""
        else:
            match = re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            if rule_id == "OB-014" and "where" not in cleaned.lower():
                continue
            snippet = cleaned[max(0, match.start() - 30) : match.end() + 30].strip()
        findings.append(
            {
                "id": rule_id,
                "level": level,
                "level_label": LEVEL_LABEL[level],
                "title": title,
                "message": message,
                "suggestion": suggestion,
                "snippet": snippet,
            }
        )
    order = {"error": 0, "warn": 1, "info": 2}
    findings.sort(key=lambda item: (order[item["level"]], item["id"]))
    return findings


def main() -> int:
    sql = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    if not sql.strip():
        print("usage: python review_rules.py \"<SQL>\"", file=sys.stderr)
        return 2
    findings = analyze(sql)
    if not findings:
        print("no issue found")
        return 0
    for finding in findings:
        print(f"[{finding['level_label']}] {finding['id']} {finding['title']}")
        print(f"    problem  : {finding['message']}")
        print(f"    suggestion: {finding['suggestion']}")
        if finding["snippet"]:
            print(f"    snippet  : {finding['snippet']}")
    print(json.dumps({"findings": findings}, ensure_ascii=False))
    return 1 if any(item["level"] == "error" for item in findings) else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
