"""Доступ к LLM через OpenAI-совместимый API (по умолчанию DeepSeek). Модель меняется переменными .env."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

import httpx
from openai import APIError, OpenAI

from . import config

log = logging.getLogger("mechanic.llm")
_client: OpenAI | None = None
_fallback: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY or "missing", timeout=60, max_retries=2)
    return _client


def fallback_client() -> OpenAI | None:
    """Резервный провайдер (OpenRouter). None, если резерв не настроен."""
    global _fallback
    if not (config.LLM_FALLBACK_MODEL and config.OPENROUTER_API_KEY):
        return None
    if _fallback is None:
        _fallback = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=config.OPENROUTER_API_KEY, timeout=60, max_retries=1,
                           http_client=httpx.Client(proxy=config.OPENROUTER_PROXY or None, trust_env=False, timeout=60))
    return _fallback


@dataclass
class Usage:
    """Учёт токенов для расчёта стоимости одного запроса (критерий «экономика»)."""
    calls: int = 0
    prompt: int = 0
    cached: int = 0
    completion: int = 0
    seconds: float = 0.0
    fallback: bool = False
    log: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, u, secs: float, kind: str = "") -> None:
        if u is None:
            return
        with self._lock:
            self.calls += 1
            self.prompt += u.prompt_tokens or 0
            self.completion += u.completion_tokens or 0
            details = getattr(u, "prompt_tokens_details", None)
            self.cached += (getattr(details, "cached_tokens", 0) or 0) if details else (getattr(u, "prompt_cache_hit_tokens", 0) or 0)
            self.seconds += secs
            self.log.append({"kind": kind, "prompt": u.prompt_tokens or 0, "completion": u.completion_tokens or 0,
                             "seconds": round(secs, 2)})

    def as_dict(self) -> dict:
        return {"calls": self.calls, "prompt_tokens": self.prompt, "cached_tokens": self.cached,
                "completion_tokens": self.completion, "llm_seconds": round(self.seconds, 2),
                "fallback_model": config.LLM_FALLBACK_MODEL if self.fallback else None}


def chat(messages: list[dict], tools: list[dict] | None = None, usage: Usage | None = None,
         temperature: float = 0.2, max_tokens: int = 1800, tool_choice: str | None = None):
    t0 = time.time()
    kw = {"model": config.LLM_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if tools:
        kw["tools"] = tools
        if tool_choice:
            kw["tool_choice"] = tool_choice   # "none" – только ответ текстом, инструменты остаются описанными
    if "deepseek" in config.LLM_BASE_URL:
        kw["extra_body"] = {"thinking": {"type": "disabled"}}
    try:
        resp = client().chat.completions.create(**kw)
    except APIError as e:
        # основная модель не ответила даже после повторов – не роняем ответ механику, а уходим на резервную
        backup = fallback_client()
        if backup is None:
            raise
        log.warning("основная LLM недоступна (%s), запрос уходит на резервную %s", type(e).__name__, config.LLM_FALLBACK_MODEL)
        kw.pop("extra_body", None)
        kw["model"] = config.LLM_FALLBACK_MODEL
        resp = backup.chat.completions.create(**kw)
        if usage is not None:
            usage.fallback = True
    msg = resp.choices[0].message
    if usage is not None:
        usage.add(resp.usage, time.time() - t0, "tools" if msg.tool_calls else "answer")
    return msg
