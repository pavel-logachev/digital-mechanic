"""Журнал работы агента: кто и что спросил, что ответили, на какие страницы сослались, какие заявки отправлены.

Пишется построчно в STATE_DIR/audit.jsonl (вне Git). Голос не сохраняется – только распознанный текст.
"""
from __future__ import annotations

import json
import threading
import time

from . import config

_lock = threading.Lock()


def write(kind: str, **fields) -> None:
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kind": kind, **fields}
    try:
        config.STATE_DIR.mkdir(parents=True, exist_ok=True)
        with _lock, open(config.STATE_DIR / "audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except (OSError, TypeError, ValueError):
        pass  # журнал не должен ломать ответ механику
