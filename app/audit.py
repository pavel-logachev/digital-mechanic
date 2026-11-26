"""Журнал работы агента: кто и что спросил, что ответили, на какие страницы сослались, какие заявки отправлены.

Пишется построчно в STATE_DIR/audit/ГГГГ-ММ.jsonl (вне Git), по файлу на месяц. Голос не сохраняется –
только распознанный текст. Файлы старше AUDIT_RETENTION_DAYS удаляются автоматически.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from . import config

_lock = threading.Lock()
_last_cleanup = 0.0


def folder() -> Path:
    return config.STATE_DIR / "audit"


def _cleanup(now: float) -> None:
    global _last_cleanup
    if now - _last_cleanup < 3600:
        return
    _last_cleanup = now
    limit = now - config.AUDIT_RETENTION_DAYS * 86400
    for path in folder().glob("*.jsonl"):
        try:
            if path.stat().st_mtime < limit:
                path.unlink()
        except OSError:
            pass


def write(kind: str, **fields) -> None:
    now = time.time()
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kind": kind, **fields}
    try:
        folder().mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(folder() / time.strftime("%Y-%m.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            _cleanup(now)
    except (OSError, TypeError, ValueError):
        pass  # журнал не должен ломать ответ механику
