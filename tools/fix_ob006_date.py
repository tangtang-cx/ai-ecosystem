#!/usr/bin/env python3
"""Add `date(` to the OB-006 function list in every implementation.

The rule "indexed column wrapped in a function" missed the most common case
`WHERE DATE(created_at) = '2026-01-01'` because `date` was not in the
alternation. Fixed in:
  * Qoder/reviewer.py            (the Streamlit app)
  * 魔搭/scripts/review_rules.py (the ModelScope Skill script)
  * Qoder/site/index.html        (the published site demo)
"""

from __future__ import annotations

from pathlib import Path

OLD = "year|month|day|date_format|substring|left|right|lower|upper|concat"
NEW = "year|month|day|date|date_format|substring|left|right|lower|upper|concat"

targets = [
    Path("Qoder/reviewer.py"),
    Path("魔搭/scripts/review_rules.py"),
    Path("Qoder/site/index.html"),
]

for path in targets:
    text = path.read_text(encoding="utf-8")
    if OLD not in text:
        print(f"skip (pattern not found): {path}")
        continue
    path.write_text(text.replace(OLD, NEW), encoding="utf-8", newline="")
    print(f"patched: {path}")
