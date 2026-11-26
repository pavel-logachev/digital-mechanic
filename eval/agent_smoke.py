"""Ручной прогон агента из консоли: python -m eval.agent_smoke VEHICLE SESSION "вопрос" ...
С флагом --fake-search использует простой поиск по тексту PDF (до сборки индекса)."""
import json
import sys
import time

from app import agent


class FakeSearcher:
    def __init__(self):
        import pymupdf
        from app import config
        from app.manuals import MANUALS
        self.pages = {}
        for m in MANUALS:
            doc = pymupdf.open(config.MANUALS_DIR / m.filename)
            for i, p in enumerate(doc, 1):
                self.pages[(m.id, i)] = p.get_text()

    def search(self, query, engine_model, k=5, rewrites=None):
        from app.manuals import manual_ids_for_engine
        ids = set(manual_ids_for_engine(engine_model))
        words = {w for q in [query] + (rewrites or []) for w in q.lower().split() if len(w) > 3}
        scored = []
        for (mid, p), t in self.pages.items():
            if mid in ids:
                tl = t.lower()
                s = sum(tl.count(w[:-2] if len(w) > 6 else w) for w in words)
                scored.append((s, mid, p, t))
        scored.sort(reverse=True)
        return [{"manual_id": m, "page": p, "score": s, "text": t, "snippet": t[:300]} for s, m, p, t in scored[:k]]

    def page_text(self, mid, page):
        return self.pages.get((mid, page), "")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--fake-search":
        agent._searcher = FakeSearcher()
        args = args[1:]
    vid, sid, *questions = args
    conv = agent.get_conversation("smoke", vid, sid)

    def emit(ev):
        if ev["type"] == "step" and ev["status"] != "running":
            print(f"  · {ev['title']}: {ev['detail']}")
        elif ev["type"] == "diagnosis":
            d = ev["data"]
            print(f"  ▶ ВЕРДИКТ {d['verdict']} {d.get('anomaly_type')} urgency={d['urgency']} rule={d['rule']}")
        elif ev["type"] == "message":
            print("\n" + ev["text"] + "\n")
            for c in ev["citations"]:
                print(f"   [{c['n']}] {c['title']} стр. {c['page']}: {c['quote'][:160]}")
            print("  usage:", json.dumps(ev.get("usage")))
        elif ev["type"] == "draft":
            print("  ▶ ЧЕРНОВИК", json.dumps(ev["draft"], ensure_ascii=False)[:800])
    for q in questions or [agent.__dict__.get("X", "Получить результат диагностики по выбранной проверке и объяснить, что делать.")]:
        print(f"\n>>> {q}")
        t0 = time.time()
        agent.Agent(conv, emit).run(q)
        print(f"  [{time.time() - t0:.1f} с]")


if __name__ == "__main__":
    main()
