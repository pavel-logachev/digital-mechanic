"""Сравнивает RRF и Jev на раскрытых контрольных вопросах."""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from statistics import median
from time import perf_counter

if not __package__:  # Также поддерживается `python eval/retrieval_eval.py`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config
from app.manuals import manuals_for_engine
from app.search import TOP_N, Searcher


def _data_dir():
    from app import config
    config.EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return config.EVAL_DATA_DIR


def _data(name):
    return _data_dir() / name

DATASET = _data("control-questions.json")
EVAL_BUDGET = 0.30
# До 100 страниц по 3200 символов; оценка резерва для Jev 1.13, с запасом на служебный JSON.
JEV_QUERY_RESERVE = 0.04


def summarize(ranks: list, times: list) -> dict:
    """Считает попадания, обратные ранги и задержку в миллисекундах."""
    hits = {str(k): sum(rank is not None and rank <= k for rank in ranks) for k in (1, 3, 5)}
    return {"n": len(ranks), "hits": hits, "hit_rates": {k: v / len(ranks) for k, v in hits.items()},
            "mrr": sum(1 / rank for rank in ranks if rank is not None) / len(ranks),
            "p50_ms": 1000 * median(times)}


def _cases(dataset, searcher):
    """Проверяет применимость золотых страниц и явность исключений."""
    cases, excluded = [], {}
    for q in dataset["questions"]:
        gold = {(ref["document_id"], ref["page_pdf"]) for ref in q["expected_pdf_pages"]}
        reason = q.get("retrieval_exclusion")
        if not gold and reason:
            excluded[q["id"]] = reason
            continue
        engine = q["selected_vehicle_engine"]
        allowed = {m.id for m in manuals_for_engine(engine)}
        if not gold or reason or any(manual_id not in allowed for manual_id, _ in gold):
            raise ValueError(f"Невалидная разметка: {q['id']}")
        for mid, p in gold:
            searcher.page_text(mid, p)
        cases.append((q, gold))
    if len(cases) != dataset["metadata"]["retrieval_question_count"]:
        raise ValueError("Число оценённых вопросов не соответствует метаданным")
    return cases, excluded


def _run(searcher, cases, enable):
    """Запускает поиск, учитывая подмену Jev на RRF и бюджет API."""
    ranks, times, rows = [], [], []
    cost, reserved, unknown_requests = 0.0, 0.0, 0
    statuses = Counter()
    for q, gold in cases:
        config.RERANK_ENABLED = enable and cost + reserved + JEV_QUERY_RESERVE <= EVAL_BUDGET
        start = perf_counter()
        hits = searcher.search(q["question"], q["selected_vehicle_engine"], k=TOP_N)
        elapsed = perf_counter() - start
        stats = searcher.rerank_stats
        if enable and not config.RERANK_ENABLED:
            stats["status"] = "budget_fallback"
        statuses[stats["status"]] += 1
        cost += stats["cost_usd"]
        unknown_requests += stats["unknown_cost_requests"]
        if stats["unknown_cost_requests"]:
            reserved += JEV_QUERY_RESERVE
        pairs = [(hit["manual_id"], hit["page"]) for hit in hits]
        rank = next((i for i, pair in enumerate(pairs, 1) if pair in gold), None)
        ranks.append(rank)
        times.append(elapsed)
        rows.append({"id": q["id"], "rank": rank, "ms": round(1000 * elapsed, 2),
                     "top5": pairs[:5], "jev": stats})
    return {**summarize(ranks, times), "rerank_statuses": dict(statuses), "usage_cost_usd": cost,
            "unknown_cost_requests": unknown_requests, "conservative_cost_usd": cost + reserved,
            "questions": rows}


def main() -> None:
    """Загружает индекс и печатает сопоставимые метрики двух режимов."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["both", "rrf", "jev"], default="both")
    parser.add_argument("--output", type=Path, help="Путь для отчёта JSON с результатами по вопросам")
    args = parser.parse_args()
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    searcher = Searcher.load()
    cases, excluded = _cases(dataset, searcher)
    old_setting = config.RERANK_ENABLED
    config.RERANK_ENABLED = False
    # Подготовка модели и первый encode не входят в задержку запроса.
    searcher.search("техническое обслуживание двигателя", cases[0][0]["selected_vehicle_engine"], k=1)
    report = {"mrr_at": TOP_N, "excluded": excluded, "runs": {}}
    try:
        for mode in ["rrf", "jev"] if args.mode == "both" else [args.mode]:
            result = _run(searcher, cases, mode == "jev")
            report["runs"][mode] = result
            n = result["n"]
            hits = " ".join(f"hit@{k}={v}/{n} ({v/n:.1%})" for k, v in result["hits"].items())
            print(f"{mode.upper()}: {hits} MRR@{TOP_N}={result['mrr']:.4f} p50={result['p50_ms']:.2f} мс; "
                  f"статусы={result['rerank_statuses']}; usage=${result['usage_cost_usd']:.6f}; "
                  f"запросов без usage={result['unknown_cost_requests']}", flush=True)
    finally:
        config.RERANK_ENABLED = old_setting
    print("Исключены:", ", ".join(excluded), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
