"""MiniMax client — OpenAI compatible, standard library only.

MiniMax exposes an OpenAI-compatible chat endpoint, so the same client is used
for MiniMax, StepFun, ModelScope and any other OpenAI-compatible gateway.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "minimax": {
        "base_url": os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.chat/v1"),
        "model": os.environ.get("MINIMAX_MODEL", "MiniMax-Text-01"),
        "env_key": "MINIMAX_API_KEY",
    },
    "modelscope": {
        "base_url": os.environ.get("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1"),
        "model": os.environ.get("MODELSCOPE_MODEL", "MiniMax/MiniMax-M3"),
        "env_key": "MODELSCOPE_API_KEY",
    },
    "stepfun": {
        "base_url": os.environ.get("STEPFUN_BASE_URL", "https://api.stepfun.com/v1"),
        "model": os.environ.get("STEPFUN_MODEL", "step-2-16k"),
        "env_key": "STEPFUN_API_KEY",
    },
}


@dataclass
class ChatResult:
    content: str
    model: str
    usage: dict
    elapsed_ms: int


class LLMError(RuntimeError):
    pass


class MiniMaxClient:
    """OpenAI-compatible chat client (MiniMax by default)."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        model: str | None = None,
        provider: str = "minimax",
        timeout: int = 90,
    ) -> None:
        preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["minimax"])
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or preset["base_url"]).rstrip("/")
        self.model = model or preset["model"]
        self.timeout = timeout

    @classmethod
    def from_env(cls, provider: str = "minimax") -> "MiniMaxClient | None":
        preset = PROVIDER_PRESETS.get(provider)
        if not preset:
            return None
        key = os.environ.get(preset["env_key"], "")
        if not key:
            return None
        return cls(key, provider=provider)

    def chat(self, messages: list[dict[str, str]], *, system: str = "", temperature: float = 0.3,
             max_tokens: int = 1024) -> ChatResult:
        import time

        if not self.api_key:
            raise LLMError("缺少 API Key：请设置 MINIMAX_API_KEY 或在界面里粘贴。")
        payload_messages = ([{"role": "system", "content": system}] if system else []) + list(messages)
        body = json.dumps(
            {
                "model": self.model,
                "messages": payload_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        started = int(time.monotonic() * 1000)
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout, context=ssl.create_default_context()
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            raise LLMError(f"HTTP {error.code}: {detail[:300]}") from error
        except Exception as error:
            raise LLMError(f"{type(error).__name__}: {error}") from error

        try:
            data = json.loads(raw.decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
        except Exception as error:
            raise LLMError(f"返回结构异常：{error}") from error
        return ChatResult(
            content=content,
            model=data.get("model", self.model),
            usage=data.get("usage", {}) or {},
            elapsed_ms=int(time.monotonic() * 1000) - started,
        )


def search_knowledge(query: str, base_url: str = "http://127.0.0.1:8848", top_k: int = 3) -> str:
    """Query the seekdb knowledge service (see dify/seekdb_service)."""
    import urllib.request

    body = json.dumps({"query": query, "top_k": top_k, "mode": "hybrid"}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/search",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("context", "")
