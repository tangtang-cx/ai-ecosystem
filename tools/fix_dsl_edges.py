#!/usr/bin/env python3
"""Fix the DSL edges: Dify only imports edges that carry type + data.sourceType/targetType.

Evidence: on the published app the LLM node reported ``predecessor_node_id: null``
and the answer node produced ``""`` -- the nodes ran unconnected, so the answer
template could not resolve ``{{#llm.text#}}``.

Dify's own exported edges look like:

    - data:
        sourceType: start
        targetType: llm
      id: start-llm
      source: start
      sourceHandle: source
      target: llm
      targetHandle: target
      type: custom

This script rewrites every edge of every DSL in Dify/ to that exact shape and
keeps the ids stable.
"""

from __future__ import annotations

import re
from pathlib import Path

DSLS = [
    "Dify/app.yml",
    "Dify/app-with-model.yml",
    "Dify/app-seekdb.yml",
    "Dify/app-rag.template.yml",
]

EDGE_RE = re.compile(
    r"(?P<indent>[ ]*)- id: (?P<id>[^\n]+)\n"
    r"(?P=indent)  source: (?P<source>[^\n]+)\n"
    r"(?P=indent)  sourceHandle: (?P<sourceHandle>[^\n]+)\n"
    r"(?P=indent)  target: (?P<target>[^\n]+)\n"
    r"(?P=indent)  targetHandle: (?P<targetHandle>[^\n]+)\n"
)


def node_types(text: str) -> dict[str, str]:
    types: dict[str, str] = {}
    for match in re.finditer(r"^      - id: (?P<id>[^\n]+)\n(?:.*\n)*?        data:\n(?:.*\n)*?          type: (?P<type>[a-z\-]+)\n", text, re.MULTILINE):
        types[match.group("id").strip()] = match.group("type")
    return types


def fix(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    types = node_types(text)

    def repl(match: re.Match[str]) -> str:
        indent = match.group("indent")
        edge_id = match.group("id").strip()
        source = match.group("source").strip()
        target = match.group("target").strip()
        source_type = types.get(source, "start")
        target_type = types.get(target, "llm")
        return (
            f"{indent}- data:\n"
            f"{indent}    sourceType: {source_type}\n"
            f"{indent}    targetType: {target_type}\n"
            f"{indent}  id: {edge_id}\n"
            f"{indent}  source: {source}\n"
            f"{indent}  sourceHandle: {match.group('sourceHandle').strip()}\n"
            f"{indent}  target: {target}\n"
            f"{indent}  targetHandle: {match.group('targetHandle').strip()}\n"
            f"{indent}  type: custom\n"
        )

    fixed = EDGE_RE.sub(repl, text)
    if fixed != text:
        path.write_text(fixed, encoding="utf-8", newline="")
        print(f"fixed edges: {path}")
    else:
        print(f"no change needed: {path}")

    # report what the edges look like now
    for match in re.finditer(r"- data:\n\s+sourceType: (\S+)\n\s+targetType: (\S+)", fixed):
        print(f"    edge {match.group(1)} -> {match.group(2)}")


for name in DSLS:
    path = Path(name)
    if path.exists():
        fix(path)
    else:
        print(f"missing: {name}")
