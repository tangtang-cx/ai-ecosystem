#!/usr/bin/env python3
"""Update the commit SHAs inside AI-Ecosystem-Solutions/README.md.

Matches on the SHA substring so the surrounding markdown cannot break it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATH = Path("AI-Ecosystem-Solutions/README.md")

UPDATES = {
    "9e0f9518c0bb265042e82f99c59c78d3ee1a2608": "15f2ac4e07b921446e79eebbdf262988874accc8",  # Dify
    "1d7511a27b1b705d314116bec8ca7ad38541ac95": "e2275fbafd575794584227686104c46221d82181",  # qoder
    "21859ebcbbe273a0e2d6cc181437bbda05ffba6d": "46299d3d294df7200142c33728a70d3fb8022558",  # modelscope
    "b03806478ee18ea0bc9469389e9da534adcaecb4": "576c8588fe5bcfbd4b66535d884914a298bda29e",  # ecosystem
}

text = PATH.read_text(encoding="utf-8")
for old, new in UPDATES.items():
    if old in text:
        text = text.replace(old, new)
        print(f"{old[:10]} -> {new[:10]}")
    else:
        print(f"skip (not present): {old[:10]}")

PATH.write_text(text, encoding="utf-8", newline="")
print("PUA chars:", sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF))
