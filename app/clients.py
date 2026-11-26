"""HTTP-клиенты внешних сервисов: ML-диагностика и ТОиР. Адреса — из .env (F6 ТЗ)."""
from __future__ import annotations

import logging
import time

import httpx

from . import config

log = logging.getLogger("mechanic.clients")
RETRIES = int(config.env("SERVICE_RETRIES", "2"))
TIMEOUT = float(config.env("SERVICE_TIMEOUT", "15"))


def _post(url: str, payload: dict, safe_to_repeat: bool) -> httpx.Response:
    """POST с повторами при сбое связи. Запрос, который мог дойти до сервиса (создание заявки),
    повторяем только при ошибке соединения – когда сервис его точно не получил, чтобы не задвоить заявку."""
    for attempt in range(RETRIES + 1):
        try:
            r = httpx.post(url, json=payload, timeout=TIMEOUT)
        except httpx.ConnectError:
            if attempt == RETRIES:
                raise
        except httpx.HTTPError:
            if not safe_to_repeat or attempt == RETRIES:
                raise
        else:
            if r.status_code < 500 or not safe_to_repeat or attempt == RETRIES:
                return r
        log.warning("повтор запроса %s (попытка %s)", url, attempt + 2)
        time.sleep(0.5 * 2 ** attempt)
    raise RuntimeError("unreachable")


class ServiceError(Exception):
    def __init__(self, service: str, status: int | None, detail: str):
        super().__init__(f"{service}: {status} {detail}")
        self.service, self.status, self.detail = service, status, detail


def diagnose(vehicle_id: str, session_id: str) -> dict:
    try:
        r = _post(f"{config.ML_URL}/diagnose", {"vehicle_id": vehicle_id, "session_id": session_id}, safe_to_repeat=True)
    except httpx.HTTPError as e:
        raise ServiceError("ML", None, f"сервис диагностики недоступен ({type(e).__name__})") from e
    if r.status_code != 200:
        raise ServiceError("ML", r.status_code, r.text[:300])
    data = r.json()
    if data.get("vehicle_id") != vehicle_id or data.get("session_id") != session_id:
        raise ServiceError("ML", 200, "ответ относится к другой машине или проверке")
    return data


def create_ticket(payload: dict) -> dict:
    try:
        r = _post(f"{config.TOIR_URL}/tickets", payload, safe_to_repeat=False)
    except httpx.HTTPError as e:
        raise ServiceError("ТОиР", None, f"система ТОиР недоступна ({type(e).__name__})") from e
    if r.status_code != 201:
        raise ServiceError("ТОиР", r.status_code, r.text[:500])
    return r.json()


def health() -> dict:
    out = {}
    for name, url in (("ml", config.ML_URL), ("toir", config.TOIR_URL)):
        try:
            out[name] = httpx.get(f"{url}/health", timeout=3).status_code == 200
        except httpx.HTTPError:
            out[name] = False
    return out
