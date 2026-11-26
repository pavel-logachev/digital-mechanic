"""Учетные записи и роли: механик (mechanic) и главный механик (chief).

Пароли хранятся только хешами PBKDF2-SHA256. Сессия – подписанная cookie (HMAC, ключ в STATE_DIR/secret.key).
Если файла пользователей нет, сервис работает без входа (стенд для жюри) или по общему ACCESS_PASSWORD.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from . import config

ROLES = {"mechanic": "Механик", "chief": "Главный механик"}
ITERATIONS = 240_000


@dataclass
class User:
    login: str
    name: str
    role: str


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2${ITERATIONS}${salt}${digest}"


def _check_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, digest)


def enabled() -> bool:
    return config.USERS_FILE.exists()


def load() -> dict[str, dict]:
    try:
        rows = json.loads(config.USERS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {r["login"].lower(): r for r in rows if r.get("login") and r.get("role") in ROLES and not r.get("disabled")}


def save(rows: list[dict]) -> None:
    config.USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.USERS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(config.USERS_FILE)


def authenticate(login: str, password: str) -> User | None:
    row = load().get((login or "").strip().lower())
    if not row or not _check_password(password or "", row.get("password", "")):
        return None
    return User(row["login"], row.get("name") or row["login"], row["role"])


def _secret() -> bytes:
    path = config.STATE_DIR / "secret.key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip().encode()


def make_session(user: User) -> str:
    body = base64.urlsafe_b64encode(json.dumps([user.login, int(time.time()) + config.SESSION_DAYS * 86400]).encode()).decode()
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def from_session(token: str) -> User | None:
    try:
        body, sig = (token or "").rsplit(".", 1)
        if not hmac.compare_digest(sig, hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()):
            return None
        login, expires = json.loads(base64.urlsafe_b64decode(body.encode()))
    except (ValueError, TypeError):
        return None
    row = load().get(str(login).lower())
    if not row or expires < time.time():
        return None  # учетку отключили или сессия истекла
    return User(row["login"], row.get("name") or row["login"], row["role"])
