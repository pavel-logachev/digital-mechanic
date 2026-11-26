"""Сквозная оценка агента на контрольных вопросах: страницы, цифры, отказы, время и токены.

python -m eval.agent_eval [--limit N] [--workers 4]
Пишет eval/agent-eval-report.json. Каждый вопрос задаётся в новом диалоге по машине с нужным двигателем.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app import agent, data, verify


def _data_dir():
    from app import config
    config.EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return config.EVAL_DATA_DIR


def _data(name):
    return _data_dir() / name

ROOT = Path(__file__).resolve().parent
REFUSAL = re.compile(r"нет данных|не (указан|приведен|приведён|нашёл|нашел|найден|описан)|в руководстве[^.]{0,60}нет|отсутству", re.I)


def vehicle_for(engine: str) -> dict:
    return next(v for v in data.vehicles() if v["engine_model"] == engine)


def run_case(q: dict) -> dict:
    v = vehicle_for(q["selected_vehicle_engine"])
    conv = agent.get_conversation("eval-" + q["id"], v["vehicle_id"], v["sessions"][-1]["session_id"])
    conv.messages.clear()
    out: dict = {"id": q["id"], "category": q["category"], "vehicle": v["vehicle_id"], "engine": v["engine_model"]}
    events: list[dict] = []
    t0 = time.time()
    try:
        agent.Agent(conv, events.append).run(q["question"])
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    out["seconds"] = round(time.time() - t0, 1)
    msg = next((e for e in reversed(events) if e["type"] == "message"), {"text": "", "citations": []})
    cited = {(c["manual_id"], c["page"]) for c in msg["citations"]}
    expected = {(p["document_id"], p["page_pdf"]) for p in q.get("expected_pdf_pages", [])}
    anchors = [s["anchor"] for s in q.get("source_verification", []) if s.get("anchor")]
    text = msg["text"]
    nums_in_answer = verify.page_numbers(text)
    out.update({
        "answer": text, "citations": [f"{m}#{p}" for m, p in sorted(cited)],
        "expected_pages": [f"{m}#{p}" for m, p in sorted(expected)],
        "page_hit": bool(cited & expected) if expected else None,
        "anchors": anchors,
        "anchor_hit": (any(all(n in nums_in_answer for n in verify.page_numbers(a)) for a in anchors) if anchors else None),
        "refused": bool(REFUSAL.search(text)),
        "verify_retry": any(e["type"] == "step" and e.get("tool") == "verify" and e["status"] == "error" for e in events),
        "unconfirmed_note": "не удалось подтвердить" in text,
        "unverified": msg.get("unverified", []), "first_pass_problems": msg.get("first_pass_problems", []),
        "steps": [e["title"] for e in events if e["type"] == "step" and e["status"] != "running"],
        "usage": conv.usage.as_dict(), "calls": conv.usage.log,
    })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    ds = json.loads((_data("control-questions.json")).read_text(encoding="utf-8"))
    qs = [q for q in ds["questions"] if q["category"] != "результат ML"]
    if a.ids:
        qs = [q for q in qs if q["id"] in a.ids.split(",")]
    if a.limit:
        qs = qs[: a.limit]
    agent.searcher()
    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(run_case, qs))
    paged = [r for r in res if r["page_hit"] is not None and r["category"] != "нет данных"]
    anch = [r for r in res if r["anchor_hit"] is not None and r["category"] in ("числовой норматив", "ловушка")]
    nodata = [r for r in res if r["category"] == "нет данных"]
    summary = {
        "questions": len(res),
        "page_hit": f"{sum(r['page_hit'] for r in paged)}/{len(paged)}",
        "numbers_match_anchor": f"{sum(r['anchor_hit'] for r in anch)}/{len(anch)}",
        "no_data_refused": f"{sum(r['refused'] for r in nodata)}/{len(nodata)}",
        "verify_retry": sum(r["verify_retry"] for r in res),
        "unconfirmed_left": sum(r["unconfirmed_note"] for r in res),
        "errors": sum(1 for r in res if r.get("error")),
        "p50_seconds": statistics.median(r["seconds"] for r in res),
        "mean_prompt_tokens": round(statistics.mean(r["usage"]["prompt_tokens"] for r in res)),
        "mean_cached_tokens": round(statistics.mean(r["usage"]["cached_tokens"] for r in res)),
        "mean_completion_tokens": round(statistics.mean(r["usage"]["completion_tokens"] for r in res)),
        "mean_llm_calls": round(statistics.mean(r["usage"]["calls"] for r in res), 2),
    }
    (_data("agent-eval-report.json")).write_text(json.dumps({"summary": summary, "results": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in res:
        flag = "OK " if r["page_hit"] or (r["category"] == "нет данных" and r["refused"]) else "-- "
        print(flag, r["id"], r["category"], r["seconds"], "c:", r["citations"][:4], "exp:", r["expected_pages"][:3],
              "anchor:", r["anchor_hit"], r.get("error", ""))


if __name__ == "__main__":
    main()
