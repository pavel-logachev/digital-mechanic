"""Reproduce the report aggregates from saved benchmark outputs, without API calls."""
from __future__ import annotations

from collections import Counter
import math
from typing import Any

from eval.quality_eval import HERE, classify_failure, read_json, ref_list, summarize, write_json


def wilson(success: int, n: int) -> list[float] | None:
    if not n:
        return None
    p, z = success / n, 1.96
    scale = 1 + z * z / n
    delta = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    center = p + z * z / (2 * n)
    return [round(100 * (center - delta) / scale, 2), round(100 * (center + delta) / scale, 2)]


def report_stats(rows):
    summary: dict[str, Any] = summarize(rows)
    success = sum((r.get('judgment') or {}).get('verdict') == ('correct' if r['answerable'] else 'refused_ok')
                  for r in rows)
    missing = [r for r in rows if r['category'] == 'нет данных']
    within_scope = [r for r in rows if r['answerable'] and r['expected_pages']]
    summary.update(strict_numerator=success, strict_wilson_95_pct=wilson(success, len(rows)),
                   no_data_ok=sum((r.get('judgment') or {}).get('verdict') == 'refused_ok' for r in missing), no_data_n=len(missing),
                   gold_page_retrieved=sum(bool(set(r['expected_pages']) & set(r.get('retrieved_pages', []))) for r in within_scope),
                   gold_page_n=len(within_scope), verify_retry=sum(bool(r.get('first_pass_problems')) for r in rows),
                   verify_remaining=sum(bool(r.get('unverified')) for r in rows),
                   failures_by_case={r['id']: r['failure'] for r in rows if r.get('failure')})
    return summary


def normalize(rows, questions, audit, stage, apply_manual=False):
    result = []
    for row in rows:
        q = questions[row['id']]
        if q.get('evaluation_exclude_reason'):
            continue
        r = {**row, 'answerable': q.get('answerable', q['category'] != 'нет данных'),
             'expected_pages': ref_list(q)}
        j = (r.get('judgment') or {}).copy()
        if j:
            if not r['citations']:
                j.update(citation_supported=False, displayed_quote_supported=False)
            if apply_manual and stage in audit.get(r['id'], {}):
                j.update(audit[r['id']][stage])
            r['judgment'] = j
        r['failure'] = classify_failure(r, j)
        result.append(r)
    return result


def main():
    questions = {q['id']: q for q in read_json(HERE / 'control-questions-v2.json')['questions']}
    manual = read_json(HERE / 'quality-manual-audit.json')['cases']
    sample = read_json(HERE / 'quality-comparison-sample.json')['ids']
    before = read_json(HERE / 'quality-v2-before.json')['rows']
    after = read_json(HERE / 'quality-v2-after-flash.json')['rows']
    rescored = {r['id']: r for r in read_json(HERE / 'quality-v2-before-rejudge.json')['rows']}
    # Preserve the first decision when present. Replace missing decisions only, and apply the separately logged manual audit.
    before = [r if r.get('judgment') else rescored.get(r['id'], r) for r in before]
    assert len(before) == len(after) == 72 and {r['id'] for r in before} == {r['id'] for r in after}
    stats: dict[str, Any] = {'before_audited': report_stats(normalize(before, questions, manual, 'before', True)),
             'after_audited': report_stats(normalize(after, questions, manual, 'after', True)),
             'before_judge': report_stats(normalize(before, questions, manual, 'before')),
             'after_judge': report_stats(normalize(after, questions, manual, 'after'))}
    model_rows = {'deepseek-flash': [r for r in after if r['id'] in sample]}
    for p in sorted(HERE.glob('quality-v2-compare-*.json')):
        d = read_json(p)
        model_rows[d['meta']['model']] = d['rows']
    common = set(sample).intersection(*(set(r['id'] for r in model) for model in model_rows.values()))
    for model, rows in model_rows.items():
        assert len(rows) == len({r['id'] for r in rows}) and set(r['id'] for r in rows) <= set(sample), model
    stats['comparison'] = dict(sample_size=len(sample), common_ids=[x for x in sample if x in common],
                               coverage={m: len(rows) for m, rows in model_rows.items()},
                               results={m: report_stats(normalize([r for r in rows if r['id'] in common], questions, manual, 'comparison'))
                                        for m, rows in model_rows.items()})
    stats['calibration'] = {}
    for stage, rows in (('before', before), ('after', after)):
        rs = {r['id']: r for r in rows}
        fields = ('verdict', 'citation_supported', 'displayed_quote_supported')
        stats['calibration'][stage] = {field: sum(bool(rs[id].get('judgment')) and rs[id]['judgment'].get(field) == a[stage][field]
                                                 for id, a in manual.items()) for field in fields}
        stats['calibration'][stage]['n'] = len(manual)
    start = read_json(HERE / 'quality-budget-start.json')
    end = HERE / 'quality-budget-end.json'
    if end.exists():
        final = read_json(end)
        stats['budget'] = dict(openrouter_account_delta_usd=round(final['openrouter_usage'] - start.get('openrouter_usage_before_preflight', start['openrouter_usage']), 8),
                               openrouter_main_delta_usd=round(final['openrouter_usage'] - start['openrouter_usage'], 8),
                               deepseek_account_delta_usd=round(start['deepseek_remaining'] - final['deepseek_remaining'], 2))
    counts = Counter(q['category'] for q in questions.values())
    stats['dataset'] = dict(n=len(questions), categories=dict(counts))
    write_json(HERE / 'quality-summary.json', stats)
    for k, v in stats.items():
        print(k, v)


if __name__ == '__main__':
    main()
