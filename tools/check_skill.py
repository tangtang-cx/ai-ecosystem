#!/usr/bin/env python3
"""Validate the competition SKILL.md contract without third-party dependencies."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_BYTES = 128 * 1024


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        fail("SKILL.md must start with '---' YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        fail("frontmatter is not closed with '---'")
    block = text[4:end]
    values: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            fail(f"unsupported frontmatter line: {line!r}")
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: python tools/check_skill.py gaode/SKILL.md")
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        fail(f"file is {len(raw)} bytes, over the {MAX_BYTES} byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        fail(f"file is not UTF-8: {error}")

    front = parse_frontmatter(text)
    for key in ("name", "description"):
        if not front.get(key):
            fail(f"missing non-empty frontmatter field: {key}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", front["name"]):
        fail("name must be lower-case kebab-case")

    body = text.split("\n---\n", 1)[1]
    required = (
        "maps_around_search",
        "maps_search_detail",
        "maps_direction_walking",
        "硬性规则",
        "执行流程",
        "回答模板",
    )
    missing = [item for item in required if item not in body]
    if missing:
        fail(f"missing required content: {', '.join(missing)}")

    print(f"OK: {path} ({len(raw)} bytes, name={front['name']})")


if __name__ == "__main__":
    main()
