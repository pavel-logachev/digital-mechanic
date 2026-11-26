"""Сквозная проверка всего цикла механика на всех машинах парка через HTTP API живого сервиса.

python -m eval.e2e_fleet --base http://127.0.0.1:8020 --out data/eval/e2e-fleet.json

Для каждой машины: «Получить результат диагностики» по последней проверке → правила вердикта →
ссылки только на руководства двигателя этой машины → «Создать заявку» → проверка черновика по контракту
Mock ТОиР (раздел 5 ТЗ) → подтверждение → ticket_id → повторное подтверждение не создает вторую заявку →
заявка видна в карточке машины. Для «нормы» и «сбоя записи» заявка создаваться не должна.
Запускать на отдельном экземпляре со своим STATE_DIR: тест создает заявки в заглушке ТОиР.
В отчет пишутся только агрегаты и коды, без текстов руководств.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from app.manuals import manual_ids_for_engine

URGENCY = {"low", "medium", "high"}


def chat(c: httpx.Client, body: dict) -> tuple[list[dict], float]:
    t0 = time.time()
    events = []
    with c.stream("POST", "/api/chat", json=body, timeout=240) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events, time.time() - t0


def first(events, kind):
    return next((e for e in events if e["type"] == kind), None)


def check_vehicle(base: str, vid: str) -> dict:
    out = {"vehicle": vid, "problems": []}
    bad = out["problems"].append
    with httpx.Client(base_url=base, timeout=60) as c:
        card = c.get(f"/api/vehicles/{vid}").json()
        allowed = set(manual_ids_for_engine(card["engine_model"]))
        last = sorted(card["sessions"], key=lambda s: s["checked_at"])[-1]
        cid = f"e2e-{vid}-{int(time.time())}"
        ev, sec = chat(c, {"conversation_id": cid, "vehicle_id": vid, "session_id": last["session_id"], "action": "diagnose"})
        out["diagnose_seconds"] = round(sec, 1)
        d = (first(ev, "diagnosis") or {}).get("data")
        msg = first(ev, "message")
        if first(ev, "error"):
            bad("ошибка при диагностике: " + first(ev, "error")["text"][:120])
        if not d:
            bad("нет карточки вердикта")
            return out
        out.update(ml_status=last["status"], verdict=d["verdict"], rule=d.get("rule"), urgency=d.get("urgency"), confidence=d.get("confidence"),
                   ticket_allowed=d.get("ticket_allowed"), inspect_first=d.get("inspect_first"), code=last.get("anomaly_type"))
        # правила F3 ТЗ и брифа заказчика
        if last["status"] == "check_failed" or last.get("signal_quality") == "bad":
            if d["verdict"] != "check_failed" or d.get("ticket_allowed") or d.get("urgency"):
                bad("сбой записи обработан не как сбой")
        if last["status"] == "normal" and d["verdict"] == "anomaly":
            bad("норма превратилась в отклонение")
        if d.get("rule") == "R3-not-applicable":
            # класс не подходит к двигателю: заявки нет, приоритета нет, механик получает текст рекомендации (#96, #103)
            if d.get("ticket_allowed") or d.get("urgency") or not d.get("defect_note"):
                bad("неприменимый класс: должна быть рекомендация на дефектовку без заявки и приоритета")
        elif d["verdict"] == "anomaly" and d.get("urgency") not in URGENCY:
            bad("у отклонения нет приоритета")
        if d.get("verdict") != "check_failed" and d.get("confidence") is not None and d.get("conf_threshold") is None:
            bad("порог уверенности не передан в интерфейс (#101)")
        if d.get("rule") == "R4-critical" and d.get("urgency") != "high":
            bad("критичная неисправность не с высоким приоритетом")
        cites = (msg or {}).get("citations") or []
        out["citations"] = len(cites)
        foreign = [x["manual_id"] for x in cites if x.get("manual_id") not in allowed]
        if foreign:
            bad(f"ссылки на чужие руководства: {foreign}")
        if d["verdict"] == "anomaly" and not cites and d.get("applicable") != "no":
            bad("объяснение отклонения без ссылок на руководство")
        if d["verdict"] == "check_failed" and cites:
            bad("при сбое записи агент ссылается на нормы двигателя")
        out["usage"] = (msg or {}).get("usage")
        if first(ev, "draft"):
            bad("черновик заявки появился без просьбы механика")

        # заявка
        ev2, sec2 = chat(c, {"conversation_id": cid, "vehicle_id": vid, "session_id": last["session_id"], "action": "draft_ticket"})
        draft = (first(ev2, "draft") or {}).get("draft")
        out["draft_seconds"] = round(sec2, 1)
        u1, u2 = out.get("usage") or {}, ((first(ev2, "message") or {}).get("usage") or {})
        if u2:   # usage в сообщении накопительный по разговору: расход шага заявки = разница
            out["draft_usage"] = {k: u2.get(k, 0) - u1.get(k, 0) for k in ("calls", "prompt_tokens", "cached_tokens", "completion_tokens")}
        if not d.get("ticket_allowed"):
            if draft:
                bad("черновик создан там, где заявка запрещена")
            r = c.post("/api/tickets/confirm", json={"draft_id": "D-нет"})
            if r.status_code == 200:
                bad("подтверждение несуществующего черновика прошло")
            return out
        if not draft:
            bad("агент не подготовил черновик при разрешенной заявке")
            return out
        # контракт Mock ТОиР: все поля обязательны
        if draft.get("anomaly_type") != last.get("anomaly_type"):
            bad("тип неисправности в черновике не из /diagnose")
        if not str(draft.get("conclusion", "")).strip():
            bad("пустое заключение")
        if draft.get("urgency") != d.get("urgency"):
            bad("приоритет черновика не совпадает с рассчитанным программой")
        if not draft.get("operations") or not all(str(o).strip() for o in draft["operations"]):
            bad("нет работ")
        if not isinstance(draft.get("spare_parts"), list):
            bad("запчасти не списком")
        refs = draft.get("references") or []
        if not refs or any(not r.get("manual") or not isinstance(r.get("pdf_page"), int) or r["pdf_page"] < 1 for r in refs):
            bad("ссылки заявки не по контракту")
        if any(r.get("manual_id") not in allowed for r in refs):
            bad("ссылка заявки на чужое руководство")
        out.update(operations=len(draft.get("operations") or []), parts=len(draft.get("spare_parts") or []), references=len(refs))
        edits = {"draft_id": draft["draft_id"]}
        if d.get("inspect_first"):
            edits["inspection_confirmed"] = True
        r1 = c.post("/api/tickets/confirm", json=edits)
        r2 = c.post("/api/tickets/confirm", json=edits)
        if r1.status_code != 200 or not str(r1.json().get("ticket_id", "")).startswith("TKT-"):
            bad(f"заявка не создана: {r1.status_code} {r1.text[:120]}")
            return out
        tid = r1.json()["ticket_id"]
        out["ticket_id"] = tid
        if r2.status_code != 200 or r2.json().get("ticket_id") != tid:
            bad("повторное подтверждение создало другую заявку")
        if not any(t["ticket_id"] == tid for t in c.get(f"/api/vehicles/{vid}").json()["tickets"]):
            bad("заявки нет в истории машины")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", default="http://127.0.0.1:8020")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    vids = [v["vehicle_id"] for v in httpx.get(a.base + "/api/vehicles", timeout=30).json()]
    if a.limit:
        vids = vids[:a.limit]
    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(lambda v: _safe(a.base, v), vids))
    fails = [r for r in rows if r["problems"]]
    lat = [r["diagnose_seconds"] for r in rows if "diagnose_seconds" in r]
    summary = {
        "vehicles": len(rows), "passed": len(rows) - len(fails), "failed": len(fails),
        "verdicts": {k: sum(r.get("verdict") == k for r in rows) for k in ("normal", "anomaly", "check_failed")},
        "inspect_first": sum(bool(r.get("inspect_first")) for r in rows),
        "tickets_created": sum(bool(r.get("ticket_id")) for r in rows),
        "defect_notes_without_ticket": sum(r.get("rule") == "R3-not-applicable" for r in rows),
        "diagnose_p50_seconds": round(statistics.median(lat), 1) if lat else None,
        "diagnose_max_seconds": max(lat) if lat else None,
        "draft_p50_seconds": round(statistics.median([r["draft_seconds"] for r in rows if "draft_seconds" in r] or [0]), 1),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in fails:
        print(r["vehicle"], r.get("verdict"), r.get("rule"), "|", "; ".join(r["problems"]))


def _safe(base, vid):
    try:
        return check_vehicle(base, vid)
    except Exception as e:  # noqa: BLE001 – падение одной машины фиксируем, остальные проверяем
        return {"vehicle": vid, "problems": [f"исключение {type(e).__name__}: {str(e)[:160]}"]}


if __name__ == "__main__":
    main()
