"""Доступ к LLM через OpenAI-совместимый API (по умолчанию DeepSeek). Модель меняется переменными .env."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from openai import OpenAI

from . import config

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY or "missing", timeout=60, max_retries=2)
    return _client


@dataclass
class Usage:
    """Учёт токенов для расчёта стоимости одного запроса (критерий «экономика»)."""
    calls: int = 0
    prompt: int = 0
    cached: int = 0
    completion: int = 0
    seconds: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, u, secs: float) -> None:
        if u is None:
            return
        with self._lock:
            self.calls += 1
            self.prompt += u.prompt_tokens or 0
            self.completion += u.completion_tokens or 0
            details = getattr(u, "prompt_tokens_details", None)
            self.cached += (getattr(details, "cached_tokens", 0) or 0) if details else (getattr(u, "prompt_cache_hit_tokens", 0) or 0)
            self.seconds += secs

    def as_dict(self) -> dict:
        return {"calls": self.calls, "prompt_tokens": self.prompt, "cached_tokens": self.cached,
                "completion_tokens": self.completion, "llm_seconds": round(self.seconds, 2)}


def chat(messages: list[dict], tools: list[dict] | None = None, usage: Usage | None = None,
         temperature: float = 0.2, max_tokens: int = 1800):
    t0 = time.time()
    kw = dict(model=config.LLM_MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if tools:
        kw["tools"] = tools
    if "deepseek" in config.LLM_BASE_URL:
        kw["extra_body"] = {"thinking": {"type": "disabled"}}
    resp = client().chat.completions.create(**kw)
    if usage is not None:
        usage.add(resp.usage, time.time() - t0)
    return resp.choices[0].message
