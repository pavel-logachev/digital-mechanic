"""HTTP-клиенты внешних сервисов: ML-диагностика и ТОиР. Адреса — из .env (F6 ТЗ)."""
from __future__ import annotations

import httpx

from . import config


class ServiceError(Exception):
    def __init__(self, service: str, status: int | None, detail: str):
        super().__init__(f"{service}: {status} {detail}")
        self.service, self.status, self.detail = service, status, detail


def diagnose(vehicle_id: str, session_id: str) -> dict:
    try:
        r = httpx.post(f"{config.ML_URL}/diagnose", json={"vehicle_id": vehicle_id, "session_id": session_id}, timeout=15)
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
        r = httpx.post(f"{config.TOIR_URL}/tickets", json=payload, timeout=15)
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
