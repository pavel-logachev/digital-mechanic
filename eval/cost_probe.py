"""Замер токенов и стоимости для расчёта экономики: N нажатий «Получить результат диагностики» + вопросы.

python -m eval.cost_probe  → eval/cost-probe.json
"""
import json
import statistics
import time

from app import agent, data


def _data_dir():
    from app import config
    config.EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return config.EVAL_DATA_DIR


def _data(name):
    return _data_dir() / name

CASES = [("E549YT198", "S-0011"), ("P854BT78", "S-0021"), ("P456AT178", "S-0003"), ("E549YT198", "S-0012")]


def main():
    agent.searcher()
    out = []
    for vid, sid in CASES + [(v["vehicle_id"], v["sessions"][-1]["session_id"]) for v in data.vehicles()[:6]]:
        conv = agent.get_conversation(f"cost-{vid}-{sid}", vid, sid)
        conv.messages.clear()
        ev = []
        t0 = time.time()
        agent.Agent(conv, ev.append).run("Получить результат диагностики по выбранной проверке и объяснить, что делать.")
        searches = sum(1 for e in ev if e["type"] == "step" and e["tool"] == "search_manual" and e["status"] == "done")
        d = next((e["data"] for e in ev if e["type"] == "diagnosis"), {})
        out.append({"vehicle": vid, "session": sid, "verdict": d.get("verdict"), "seconds": round(time.time() - t0, 1),
                    "searches": searches, **conv.usage.as_dict()})
        print(out[-1], flush=True)
    keys = ("calls", "prompt_tokens", "cached_tokens", "completion_tokens", "searches", "seconds")
    summary = {k: round(statistics.mean(r[k] for r in out), 2) for k in keys}
    _data("cost-probe.json").write_text(json.dumps({"summary": summary, "runs": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SUMMARY", summary)


if __name__ == "__main__":
    main()
