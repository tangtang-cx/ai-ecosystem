#!/usr/bin/env python3
"""Repair double-encoded (mojibake) text files.

Some edits were applied by a tool that decoded UTF-8 files with the Windows
ANSI codepage (GBK) and then stored the result back as UTF-8, which turns
"魔搭社区" into "榄旀惌绀惧尯" and so on.

The repair is the standard inverse: encode the mojibake text back to GBK bytes
and decode those bytes as UTF-8. Only lines that actually look like mojibake
are touched, so ASCII and correctly encoded lines stay untouched.

    python tools/fix_mojibake.py [paths...]
"""

from __future__ import annotations

import sys
from pathlib import Path

MARKERS = (
    "锛", "銆", "鈥", "娴", "绗", "鏂", "鐨", "鍙", "闇", "鏄", "浜", "妫", "璇", "鍒", "娴",
    "榛", "挎", "幙", "绀", "鸿", "櫕", "鐨", "棰", "浠", "utup", "洿", "€", "�",
)


def looks_broken(text: str) -> bool:
    hits = sum(text.count(marker) for marker in MARKERS)
    if hits < 2:
        return False
    # a correctly encoded Chinese line rarely mixes these markers
    return hits >= 2


def repair_line(text: str) -> tuple[str, bool]:
    if not looks_broken(text):
        return text, False
    for encoding in ("gbk", "cp936", "gb18030"):
        try:
            fixed = text.encode(encoding, errors="strict").decode("utf-8", errors="strict")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if fixed != text:
            return fixed, True
    return text, False


def fix_file(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    lines = raw.split("\n")
    changed = 0
    for index, line in enumerate(lines):
        fixed, did = repair_line(line)
        if did:
            lines[index] = fixed
            changed += 1
    if changed:
        path.write_text("\n".join(lines), encoding="utf-8", newline="")
    return changed


def main() -> int:
    targets = [Path(item) for item in sys.argv[1:]]
    if not targets:
        targets = [
            path
            for path in Path(".").rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".md", ".yml", ".yaml", ".py", ".json", ".txt", ".mjs"}
            and not {"node_modules", ".git", ".data", ".cache"} & set(path.parts)
        ]
    total = 0
    for path in targets:
        try:
            changed = fix_file(path)
        except Exception as error:
            print(f"skip {path}: {error}")
            continue
        if changed:
            total += changed
            print(f"repaired {changed} lines: {path}")
    print(f"done, {total} lines repaired")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
