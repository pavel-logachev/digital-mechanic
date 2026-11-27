"""Тесты правил, которые держит код, а не модель: приоритет, плохая запись, применимость, ссылки и цифры, заявка."""
import json
from pathlib import Path

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
    # инструкции по такому узлу в руководстве нет: заявку продукт не отправляет, механик получает текст рекомендации
    assert v.rule == "R3-not-applicable" and v.urgency is None and not v.ticket_allowed and v.warnings
    assert v.defect_note and code in v.defect_note and "дефектовк" in v.defect_note
    # разъяснение заказчика: карточка машины главнее – это ошибка модели, а не диагноз; повторить проверку или дефектовка
    assert "ошибка модели" in v.action and "Повторите проверку" in v.action and "дефектовк" in v.action
    assert any("ошибка программы оценки звука, а не диагноз" in w for w in v.warnings)


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


CUSTOMER_FLEET = Path(__file__).resolve().parent.parent / "mocks" / "data" / "vehicles.json"


@pytest.mark.parametrize("source", ["fixture", "customer"])
def test_all_sessions_evaluate(source):
    """Каждая проверка парка разбирается правилами. Данные заказчика – только если скачаны локально (в Git их нет)."""
    if source == "customer":
        if not CUSTOMER_FLEET.exists():
            pytest.skip("данные заглушек заказчика не скачаны: python -m tools.fetch_materials")
        fleet = json.loads(CUSTOMER_FLEET.read_text(encoding="utf-8"))["vehicles"]
    else:
        fleet = data.vehicles()
    for v in fleet:
        for s in v["sessions"]:
            r = evaluate(s, v["engine_model"], v["sessions"])
            # без приоритета: норма, сбой записи и класс, неприменимый к двигателю (заявку продукт не отправляет)
            assert (r.urgency is None) == (r.verdict != "anomaly" or r.rule == "R3-not-applicable")
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


def test_priority_actions_are_recommendations_matching_customer_meaning():
    """#102: high – дефектовка до выпуска в рейс, medium – на ближайшем ТО, low – на следующей проверке; запрет не пишем."""
    crit = _s("S1", code="F02", score=0.9, conf=0.9)
    med = _s("S2", code="F04", score=0.6, conf=0.7)
    low = _s("S3", code="F11", score=0.5, conf=0.9)
    a = evaluate(crit, "ЯМЗ-536", [crit]).action
    assert a.startswith("Рекомендация: дефектовка до выпуска в рейс")
    assert "ближайшем ТО" in evaluate(med, "ЯМЗ-536", [med]).action
    assert "следующей проверке" in evaluate(low, "ЯМЗ-536", [low]).action
    for s in (crit, med, low):
        act = evaluate(s, "ЯМЗ-536", [s]).action.lower()
        assert "не выпускать" not in act and "запрещ" not in act and "нельзя" not in act


def test_doubtful_signal_shows_threshold():
    """#101: порог уверенности показываем механику числом."""
    s = _s("S1", code="F04", score=0.6, conf=0.55)
    v = evaluate(s, "ЯМЗ-536", [s])
    assert v.inspect_first and any("ниже порога 0,60" in w for w in v.warnings)
    assert v.as_dict()["conf_threshold"] == 0.6


def test_page_covers_unit():
    from app.faults import page_covers_unit
    body = " ".join(["Проверка давления масла контрольным манометром на прогретом двигателе."] * 8)
    assert page_covers_unit("F02", body)
    assert not page_covers_unit("F02", " ".join(["Регулировка тепловых зазоров клапанов."] * 8))
    assert not page_covers_unit("F02", "Содержание " + "давление масла ...... 19 " * 20)


def test_warning_quality_always_warns():
    """#101: при качестве warning предупреждение есть в любом вердикте – норма, отклонение, неприменимый класс."""
    for code, engine, _status in (("F04", "ЯМЗ-536", "anomaly"), ("F14", "ЯМЗ-236М2", "anomaly"), (None, "ЯМЗ-536", "normal")):
        s = _s("S1", code=code, q="warning", score=0.7, conf=0.8) if code else _s("S1", status="normal", q="warning")
        v = evaluate(s, engine, [s])
        assert any("помехами" in w for w in v.warnings), (code, v.rule, v.warnings)
