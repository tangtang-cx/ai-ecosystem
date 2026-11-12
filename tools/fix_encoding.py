#!/usr/bin/env python3
"""Repair mixed-encoding markdown files.

Some edits were applied while the tool decoded UTF-8 files with the Windows
ANSI codepage (GBK), which wrote GBK bytes back into otherwise UTF-8 files.
This script walks the file line by line: every line that is valid UTF-8 is kept
as-is, every line that is not valid UTF-8 is decoded as GBK and re-encoded as
UTF-8. The result is a consistent UTF-8 file.

    python tools/fix_encoding.py [paths...]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOTS = ["README.md", "AI-Ecosystem-Solutions", "Dify", "Qoder", "modelscope", "gaode", "stepfun", "minimax", "tools", "modelscope", "魔搭"]


def fix_file(path: Path) -> bool:
    raw = path.read_bytes()
    try:
        raw.decode("utf-8")
        return False
    except UnicodeDecodeError:
        pass

    fixed_lines: list[str] = []
    changed = False
    for line in raw.split(b"\n"):
        try:
            fixed_lines.append(line.decode("utf-8"))
        except UnicodeDecodeError:
            try:
                fixed_lines.append(line.decode("gbk"))
            except UnicodeDecodeError:
                fixed_lines.append(line.decode("utf-8", errors="replace"))
            changed = True

    text = "\n".join(fixed_lines)
    path.write_text(text, encoding="utf-8", newline="")
    return changed


def main() -> int:
    roots = [Path(item) for item in sys.argv[1:]] or [Path(item) for item in ROOTS if Path(item).exists()]
    fixed = []
    for root in roots:
        candidates = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for path in candidates:
            if path.suffix.lower() not in {".md", ".yml", ".yaml", ".py", ".json", ".txt", ".mjs", ".ps1"}:
                continue
            if "node_modules" in path.parts or ".git" in path.parts:
                continue
            try:
                if fix_file(path):
                    fixed.append(str(path))
            except Exception as error:  # pragma: no cover
                print(f"skip {path}: {error}")
    if fixed:
        print("repaired:")
        for item in fixed:
            print("  ", item)
    else:
        print("all files are already valid UTF-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
