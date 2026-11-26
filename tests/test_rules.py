"""Тесты правил, которые держит код, а не модель: приоритет, плохая запись, применимость, ссылки и цифры, заявка."""
import pytest

from app import data, verify
from app.priority import evaluate


def _s(sid, status="anomaly", code="F02", score=0.8, conf=0.85, q="good", day="01"):
    return {"session_id": sid, "checked_at": f"2026-11-{day}T10:00:00+03:00", "vehicle_id": "X", "status": status,
            "anomaly_type": code if status == "anomaly" else None, "anomaly_title": "т", "anomaly_score": None if status == "check_failed" else score,
            "confidence": None if status == "check_failed" else conf, "signal_quality": "bad" if status == "check_failed" else q,
            "description": "", "model_version": "mock-v1"}


def test_bad_record_blocks_everything():
    s = _s("S1", status="check_failed")
    v = evaluate(s, "ЯМЗ-236М2", [s])
    assert v.verdict == "check_failed" and v.urgency is None and not v.ticket_allowed


def test_bad_quality_even_with_anomaly_is_failed():
    s = _s("S1", q="bad", score=0.99, conf=0.99)
    v = evaluate(s, "ЯМЗ-236М2", [s])
    assert v.verdict == "check_failed" and not v.ticket_allowed


def test_critical_is_high():
    s = _s("S1", code="F02", score=0.6, conf=0.55)
    assert evaluate(s, "ЯМЗ-536", [s]).urgency == "high"


def test_significant_weak_is_medium_strong_is_high():
    weak = _s("S1", code="F04", score=0.6, conf=0.7)
    strong = _s("S2", code="F04", score=0.8, conf=0.85)
    assert evaluate(weak, "ЯМЗ-536", [weak]).urgency == "medium"
    assert evaluate(strong, "ЯМЗ-536", [strong]).urgency == "high"


@pytest.mark.parametrize("code,engine", [("F14", "ЯМЗ-236М2"), ("F12", "ЯМЗ-536"), ("F08", "ЗМЗ-5234.10"), ("F09", "ЗМЗ-40905.10")])
def test_not_applicable_class_flagged(code, engine):
    s = _s("S1", code=code)
    v = evaluate(s, engine, [s])
    assert v.rule == "R3-not-applicable" and v.urgency == "medium" and v.warnings


def test_normal_after_unresolved_critical_warns():
    old = _s("S1", code="F03", day="01")
    now = _s("S2", status="normal", score=0.1, conf=0.8, day="05")
    v = evaluate(now, "ЯМЗ-236М2", [old, now], tickets=[])
    assert v.verdict == "normal" and v.rule == "R2-normal-unresolved" and not v.ticket_allowed
    v2 = evaluate(now, "ЯМЗ-236М2", [old, now], tickets=[{"session_id": "S1"}])
    assert v2.rule == "R2-normal"


def test_future_sessions_ignored():
    now = _s("S1", code="F04", score=0.6, conf=0.7, day="01")
    later = _s("S2", code="F04", score=0.9, conf=0.9, day="09")
    assert evaluate(now, "ЯМЗ-536", [now, later]).urgency == "medium"


def test_all_customer_sessions_evaluate():
    for v in data.vehicles():
        for s in v["sessions"]:
            r = evaluate(s, v["engine_model"], v["sessions"])
            assert (r.urgency is None) == (r.verdict != "anomaly")
            assert r.reasons


PAGES = {("yamz-236_rk_2014", 12): "Давление в масляной системе, кПа при минимальных оборотах холостого хода, не менее 100 (1,0)"}


def _pt(m, p):
    return PAGES.get((m, p), "")


def test_verify_accepts_number_from_page():
    c = verify.check("Не менее 100 кПа (1,0 кгс/см²) {yamz-236_rk_2014#12}.", {"yamz-236_rk_2014"},
                     {("yamz-236_rk_2014", 12)}, _pt, set())
    assert not c.problems and c.citations[0]["page"] == 12 and "[1]" in c.text


def test_verify_rejects_invented_number():
    c = verify.check("Не менее 250 кПа {yamz-236_rk_2014#12}.", {"yamz-236_rk_2014"}, {("yamz-236_rk_2014", 12)}, _pt, set())
    assert any("250" in p for p in c.problems)


def test_verify_rejects_foreign_engine_and_unseen_page():
    c = verify.check("Зазор 0,25 мм {zmz-5234_rk_2025#40}. Ещё {yamz-236_rk_2014#99}.", {"yamz-236_rk_2014"},
                     {("yamz-236_rk_2014", 12)}, _pt, set())
    assert any("чужое" in p for p in c.problems) and any("не открывал" in p for p in c.problems)
    assert not c.citations


def test_verify_ignores_dates_and_ids():
    c = verify.check("Проверка S-0012 от 10.11.2026 — норма.", set(), set(), _pt, set())
    assert not c.problems
