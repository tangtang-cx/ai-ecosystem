#!/usr/bin/env python3
"""Smoke test for the ModelScope inference API.

Checks three things without starting Streamlit:

1. ``GET /v1/models`` works and returns the model catalogue (no auth needed);
2. ``POST /v1/chat/completions`` with a real API key returns a completion;
3. the chosen model id is actually present in the catalogue.

Usage:

    export MODELSCOPE_API_KEY=xxxxxxxx
    python scripts/smoke_test.py
    python scripts/smoke_test.py --model deepseek-ai/DeepSeek-V4.1-Flash --prompt "你好"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modelscope_client import (  # noqa: E402
    DEFAULT_MODEL,
    ModelScopeClient,
    ModelScopeError,
    pick_model,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="ModelScope API smoke test")
    parser.add_argument("--api-key", default=os.environ.get("MODELSCOPE_API_KEY", ""))
    parser.add_argument("--base-url", default=os.environ.get("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"))
    parser.add_argument("--model", default=os.environ.get("MODELSCOPE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--prompt", default="用一句话介绍 OceanBase 的向量检索能力。")
    args = parser.parse_args()

    client = ModelScopeClient(args.api_key, base_url=args.base_url, model=args.model)

    print(f"[1/3] GET {client.base_url}/models")
    try:
        models = client.list_models()
    except ModelScopeError as error:
        print(f"    FAIL: {error}")
        return 1
    print(f"    OK: {len(models)} 个模型可用")
    for item in models[:8]:
        print(f"      - {item}")
    if len(models) > 8:
        print(f"      ... 其余 {len(models) - 8} 个省略")

    chosen = pick_model(models, args.model)
    print(f"[2/3] 选定模型: {chosen}")

    if not args.api_key:
        print("[3/3] 跳过对话测试（没有 MODELSCOPE_API_KEY）")
        print("      设置环境变量后重跑：export MODELSCOPE_API_KEY=xxxxxxxx")
        return 0

    print(f"[3/3] POST {client.base_url}/chat/completions")
    try:
        result = client.chat(
            [
                {"role": "system", "content": "你是 OceanBase 数据库的资深工程师，回答简洁准确。"},
                {"role": "user", "content": args.prompt},
            ],
            model=chosen,
            temperature=0.3,
            max_tokens=256,
        )
    except ModelScopeError as error:
        print(f"    FAIL: {error}")
        return 1

    print(f"    OK: {result.elapsed_ms} ms  usage={result.usage}")
    print("    ---")
    print(result.content)
    print("    ---")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
