"""Распознавание голосового вопроса механика (аудио → текст) через мультимодальную модель OpenRouter.

Модель задаётся STT_MODEL в .env (по умолчанию google/gemini-3.5-flash-lite: русский, узбекский, таджикский,
киргизский, казахский, хинди, английский; ~2–3 с и ~$0,0001 на 10 секунд речи).
"""
from __future__ import annotations

import base64

import httpx

from . import config

LANG_NAMES = {"ru": "русский", "uz": "узбекский", "tg": "таджикский", "ky": "киргизский", "kk": "казахский",
              "hi": "хинди", "en": "английский"}
FORMATS = {"webm": "webm", "ogg": "ogg", "opus": "ogg", "mp4": "mp4", "m4a": "mp4", "aac": "aac", "mpeg": "mp3",
           "mp3": "mp3", "wav": "wav", "x-wav": "wav", "wave": "wav"}
MAX_BYTES = 3_000_000


class SttError(Exception):
    pass


def audio_format(content_type: str, filename: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    sub = ct.split("/")[-1] if "/" in ct else ""
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    return FORMATS.get(sub) or FORMATS.get(ext) or "webm"


def transcribe(data: bytes, fmt: str, lang: str = "ru") -> str:
    if not config.OPENROUTER_API_KEY:
        raise SttError("распознавание речи не настроено (нет ключа)")
    if not data or len(data) > MAX_BYTES:
        raise SttError("запись пустая или слишком длинная")
    hint = LANG_NAMES.get(lang, "русский")
    prompt = (f"Это голосовой вопрос механика автосервиса о двигателе грузовика. Вероятный язык: {hint}. "
              "Распознай речь дословно на том языке, на котором говорят. Марки и модели двигателей пиши как принято "
              "(ЯМЗ-236, ЯМЗ-536, ЗМЗ-409), числа – цифрами. Верни только распознанный текст, без пояснений. "
              "Если речи нет – верни пустую строку.")
    body = {"model": config.STT_MODEL, "temperature": 0, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "input_audio", "input_audio": {"data": base64.b64encode(data).decode(), "format": fmt}}]}]}
    try:
        with httpx.Client(proxy=config.OPENROUTER_PROXY or None, timeout=30, trust_env=False) as c:
            r = c.post("https://openrouter.ai/api/v1/chat/completions", json=body,
                       headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"})
    except httpx.HTTPError as e:
        raise SttError(f"сервис распознавания недоступен ({type(e).__name__})") from e
    if r.status_code != 200:
        raise SttError(f"сервис распознавания ответил {r.status_code}")
    text = (r.json()["choices"][0]["message"].get("content") or "").strip().strip('"«»')
    return text.replace(" — ", " – ").replace("—", "–")
