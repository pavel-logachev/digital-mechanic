"""Данные парка (vehicles.json), журнал заявок и состояние парка для главного механика."""
from __future__ import annotations

import json
import threading
import time
from functools import lru_cache

from . import config
from .manuals import manuals_for_engine
from .priority import evaluate


@lru_cache(maxsize=1)
def _load() -> dict:
    data = json.loads(config.VEHICLES_PATH.read_text(encoding="utf-8"))
    by_id = {}
    for v in data["vehicles"]:
        v["sessions"] = sorted(v["sessions"], key=lambda s: (s.get("checked_at", ""), s["session_id"]))
        by_id[v["vehicle_id"]] = v
    return by_id


@lru_cache(maxsize=1)
def fault_titles() -> dict[str, str]:
    return {f["code"]: f["title"] for f in json.loads(config.FAULT_TYPES_PATH.read_text(encoding="utf-8"))}


def vehicles() -> list[dict]:
    return list(_load().values())


def vehicle(vehicle_id: str) -> dict | None:
    return _load().get(vehicle_id)


def find_vehicle(query: str) -> dict | None:
    """Госномер (регистр и кириллица/латиница не важны) или гаражный номер."""
    q = _norm(query)
    for v in vehicles():
        if _norm(v["vehicle_id"]) == q or _norm(v.get("garage_no") or "") == q:
            return v
    return None


_LAT = str.maketrans("АВЕКМНОРСТУХ", "ABEKMHOPCTYX")


def _norm(s: str) -> str:
    return s.upper().replace(" ", "").replace("-", "").translate(_LAT)


def session(vehicle_id: str, session_id: str) -> dict | None:
    v = vehicle(vehicle_id)
    if not v:
        return None
    return next((s for s in v["sessions"] if s["session_id"] == session_id), None)


# ---------- журнал заявок (B1: память по машине) ----------
_lock = threading.Lock()


def _tickets_path():
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    return config.STATE_DIR / "tickets.json"


def tickets(vehicle_id: str | None = None) -> list[dict]:
    p = _tickets_path()
    items = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return [t for t in items if vehicle_id is None or t["vehicle_id"] == vehicle_id]


def add_ticket(record: dict) -> None:
    with _lock:
        items = tickets()
        record = {**record, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        items.append(record)
        _tickets_path().write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- сводки ----------
def summary(v: dict) -> dict:
    last = v["sessions"][-1] if v["sessions"] else None
    t = tickets(v["vehicle_id"])
    verdict = evaluate(last, v["engine_model"], v["sessions"], t) if last else None
    open_t = next((x["ticket_id"] for x in reversed(t) if last and x["session_id"] == last["session_id"]), None)
    if verdict is None:
        status = "ok"
    elif verdict.rule == "R4-critical":
        status = "quarantine"   # критичная неисправность без заявки: рекомендована дефектовка до выпуска в рейс
    elif verdict.verdict in ("anomaly", "check_failed") or verdict.rule in ("R2-normal-doubt", "R2-normal-unresolved"):
        status = "attention"
    else:
        status = "ok"
    keys = ("session_id", "checked_at", "status", "anomaly_type", "anomaly_title", "anomaly_score", "confidence", "signal_quality")
    return {
        "vehicle_id": v["vehicle_id"], "garage_no": v.get("garage_no"), "make": v.get("make"), "model": v.get("model"),
        "vehicle_type": v.get("vehicle_type"), "engine_model": v["engine_model"], "fuel": v.get("fuel"),
        "last_check": {k: last.get(k) for k in keys} if last else None,
        "last_urgency": verdict.urgency if verdict else None,
        "last_action": verdict.action if verdict else None,
        "last_severity": verdict.severity if verdict else None,
        "fleet_status": status, "open_ticket": open_t,
    }


def detail(vehicle_id: str) -> dict | None:
    v = vehicle(vehicle_id)
    if not v:
        return None
    out = summary(v)
    out["sessions"] = v["sessions"]
    out["tickets"] = tickets(vehicle_id)
    out["manuals"] = [{"id": m.id, "title": m.title, "designation": m.designation} for m in manuals_for_engine(v["engine_model"])]
    return out


_ORDER = {"quarantine": 0, "attention": 1, "ok": 2}
_URG = {"high": 0, "medium": 1, "low": 2, None: 3}


def fleet() -> dict:
    items = [summary(v) for v in vehicles()]
    counts = {k: sum(1 for i in items if i["fleet_status"] == k) for k in ("ok", "attention", "quarantine")}
    items.sort(key=lambda i: (_ORDER[i["fleet_status"]], _URG[i["last_urgency"]],
                              -(i["last_check"] or {}).get("anomaly_score", 0) if (i["last_check"] or {}).get("anomaly_score") is not None else 0))
    return {"counts": counts, "priority": items}
