"""ModelScope（魔搭）推理 API 客户端。

魔搭的「模型服务 / API 推理」提供 OpenAI 兼容接口：

    GET  {base_url}/models            -> 可用模型列表（无需鉴权）
    POST {base_url}/chat/completions   -> 对话补全（Bearer <API Key>）

API Key 获取路径：魔搭官网 -> 右上角头像 -> 访问令牌 -> 创建一个新的访问令牌。

本模块只用标准库，Streamlit 应用无需安装 openai SDK 即可调用。
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

DEFAULT_BASE_URL = "https://api-inference.modelscope.cn/v1"
DEFAULT_MODEL = "Qwen/Qwen3.5-27B"

# 2026-11 实测 /v1/models 返回的免费推理模型（节选，含赛题相关的 MiniMax / StepFun）
CURATED_MODELS: tuple[str, ...] = (
    "Qwen/Qwen3.5-27B",
    "Qwen/Qwen3.8-Flash-Next",
    "Qwen/Qwen3.5-122B-A10B",
    "deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "stepfun-ai/Step-3.5-Flash",
    "stepfun-ai/Step-3.7-Flash",
    "stepfun-ai/Step-5-Preview",
    "MiniMax/MiniMax-M3",
    "MiniMax/MiniMax-M1-80k",
    "ZhipuAI/GLM-4.7-Flash",
    "ZhipuAI/GLM-5.2",
    "meituan-longcat/LongCat-Flash-Lite",
    "Shanghai_AI_Laboratory/Intern-S2-Preview",
    "XGenerationLab/XiYanSQL-QwenCoder-32B-2504",
)


class ModelScopeError(RuntimeError):
    """Raised when the ModelScope API returns an error."""

    def __init__(self, message: str, *, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class ChatResult:
    content: str
    model: str
    usage: dict[str, Any]
    elapsed_ms: int


class ModelScopeClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 120,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or os.environ.get("MODELSCOPE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("MODELSCOPE_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # low level
    # ------------------------------------------------------------------ #
    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
        authenticated: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        if authenticated:
            if not self.api_key:
                raise ModelScopeError("缺少 API Key：请在左侧边栏输入魔搭访问令牌，或设置环境变量 MODELSCOPE_API_KEY。")
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout, context=ssl.create_default_context()
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise ModelScopeError(self._explain(error.code, detail), status=error.code) from error
        except urllib.error.URLError as error:
            raise ModelScopeError(f"网络请求失败：{error.reason}") from error
        except Exception as error:  # pragma: no cover - defensive
            raise ModelScopeError(f"{type(error).__name__}: {error}") from error

        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            raise ModelScopeError(f"返回内容不是 JSON：{raw[:200]!r}")

    @staticmethod
    def _explain(status: int, detail: str) -> str:
        if status == 401:
            return "API Key 无效或已过期（HTTP 401）。请到魔搭「访问令牌」页面重新创建。"
        if status == 403:
            return f"没有该模型的访问权限（HTTP 403）：{detail[:200]}"
        if status == 404:
            return f"模型不存在（HTTP 404）：{detail[:200]}"
        if status == 429:
            return "额度已用尽或触发限流（HTTP 429），请稍后再试或更换模型。"
        if status >= 500:
            return f"魔搭服务暂时不可用（HTTP {status}）：{detail[:200]}"
        return f"请求失败（HTTP {status}）：{detail[:200]}"

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def list_models(self) -> list[str]:
        """Return every model id the endpoint exposes (no auth required)."""
        data = self._request("/models", authenticated=False)
        if not isinstance(data, dict):
            return []
        return [item["id"] for item in data.get("data", []) if isinstance(item, dict) and item.get("id")]

    def chat(
        self,
        messages: Iterable[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResult:
        payload = {
            "model": model or self.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        started = _now_ms()
        data = self._request("/chat/completions", method="POST", payload=payload)
        elapsed = _now_ms() - started
        if not isinstance(data, dict):
            raise ModelScopeError(f"返回结构异常：{data!r}")
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise ModelScopeError(f"返回结构异常：{json.dumps(data, ensure_ascii=False)[:300]}")
        return ChatResult(
            content=content,
            model=data.get("model", payload["model"]),
            usage=data.get("usage", {}) or {},
            elapsed_ms=elapsed,
        )


def _now_ms() -> int:
    import time

    return int(time.monotonic() * 1000)


def pick_model(available: list[str], preferred: str = DEFAULT_MODEL) -> str:
    """Choose a model id: preferred first, then any curated match, then the first one."""
    if preferred in available:
        return preferred
    for candidate in CURATED_MODELS:
        if candidate in available:
            return candidate
    return available[0] if available else preferred
