#!/usr/bin/env python3
"""Refresh the SHA table in AI-Ecosystem-Solutions/README.md from the live refs."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

REPO = "tangtang-cx/ai-ecosystem"
PATH = Path("AI-Ecosystem-Solutions/README.md")
BRANCHES = ["Dify", "qoder", "modelscope", "gaode", "stepfun", "2026-competition-ecosystem"]

token = os.environ["GITHUB_TOKEN"]
request = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/branches?per_page=100",
    headers={"authorization": f"Bearer {token}", "accept": "application/vnd.github+json",
             "user-agent": "dsh-sha-refresh"},
)
branches = json.loads(urllib.request.urlopen(request, timeout=60).read().decode("utf-8"))
shas = {item["name"]: item["commit"]["sha"] for item in branches}

text = PATH.read_text(encoding="utf-8")
for branch in BRANCHES:
    sha = shas.get(branch)
    if not sha:
        continue
    # replace the SHA cell of the row that starts with "| <branch> |"
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line.startswith(f"| {branch} |"):
            cells = line.split("|")
            if len(cells) > 3:
                cells[3] = f" `{sha}` "
                lines[index] = "|".join(cells)
                print(f"{branch}: {sha}")
            break
    text = "\n".join(lines)

PATH.write_text(text, encoding="utf-8", newline="")
print("table refreshed; PUA chars:", sum(1 for ch in text if 0xE000 <= ord(ch) <= 0xF8FF))
