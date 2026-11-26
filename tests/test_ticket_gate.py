"""Заявка уходит в ТОиР только через confirm_ticket (кнопка механика), с проверкой полей кодом."""
import pytest

from app import agent, clients


class StubSearcher:
    def search(self, q, engine, k=5, rewrites=None):
        return [{"manual_id": "yamz-236_rk_2014", "page": 40, "score": 1, "text": "затяжка болтов крышек коренных подшипников", "snippet": ""}]

    pages = {}

    def page_text(self, m, p):
        default = " ".join(["Давление масла в системе смазки проверять контрольным манометром на прогретом двигателе."] * 6)
        return self.pages.get((m, p), default)


@pytest.fixture(autouse=True)
def stubs(monkeypatch, tmp_path):
    agent._searcher = StubSearcher()
    monkeypatch.setattr("app.config.STATE_DIR", tmp_path)
    sent = []
    monkeypatch.setattr(clients, "diagnose", lambda v, s: {
        "vehicle_id": v, "session_id": s, "status": "anomaly", "anomaly_type": "F02", "anomaly_title": "Низкое давление масла",
        "anomaly_score": 0.86, "confidence": 0.84, "signal_quality": "good", "description": "", "model_version": "mock-v1"})
    monkeypatch.setattr(clients, "create_ticket", lambda p: sent.append(p) or {"ticket_id": "TKT-0001", "status": "created"})
    return sent


def _agent():
    conv = agent.get_conversation("t1", "E549YT198", "S-0011")
    return agent.Agent(conv, lambda ev: None), conv


def test_prepare_requires_seen_reference(stubs):
    a, _ = _agent()
    out = a.t_prepare_ticket("Низкое давление", ["Проверить давление"], [], [{"manual_id": "yamz-236_rk_2014", "page": 40}])
    assert "error" in out and not stubs  # страница не была найдена поиском


def test_draft_then_confirm(stubs):
    a, conv = _agent()
    a.t_search_manual(["коренные подшипники"])
    out = a.t_prepare_ticket("Низкое давление масла", ["Проверить давление манометром"], ["вкладыши"],
                             [{"manual_id": "yamz-236_rk_2014", "page": 40}, {"manual_id": "zmz-5234_rk_2025", "page": 5}])
    assert out["urgency"] == "high" and out["rejected_references"]
    assert not stubs, "черновик не должен отправляться сам"
    res = agent.confirm_ticket(out["draft_id"], {})
    assert res["ticket_id"] == "TKT-0001"
    p = stubs[0]
    assert p["urgency"] == "high" and p["references"] == [{"manual": "236.01.01 РК", "pdf_page": 40}]
    assert set(p) == {"vehicle_id", "session_id", "anomaly_type", "conclusion", "urgency", "operations", "spare_parts", "references"}
    again = agent.confirm_ticket(out["draft_id"], {})
    assert again.get("duplicate") and len(stubs) == 1


def test_no_ticket_for_check_failed(monkeypatch, stubs):
    monkeypatch.setattr(clients, "diagnose", lambda v, s: {
        "vehicle_id": v, "session_id": s, "status": "check_failed", "anomaly_type": None, "anomaly_title": None,
        "anomaly_score": None, "confidence": None, "signal_quality": "bad", "description": "", "model_version": "mock-v1"})
    conv = agent.get_conversation("t2", "P456AT178", "S-0003")
    a = agent.Agent(conv, lambda ev: None)
    a.t_search_manual(["x"])
    out = a.t_prepare_ticket("x", ["y"], [], [{"manual_id": "yamz-236_rk_2014", "page": 40}])
    assert "error" in out and not stubs


def test_foreign_manual_page_rejected():
    a, _ = _agent()
    assert "error" in a.t_read_page("zmz-5234_rk_2025", 10)


def test_no_draft_without_instruction_for_the_unit(stubs):
    """#103: ссылка есть, но страница не про узел из типа неисправности – черновика нет, механику объясняем почему."""
    conv = agent.get_conversation("t-unit", "E549YT198", "S-0011")
    a = agent.Agent(conv, lambda ev: None)
    a.t_search_manual(["коренные подшипники"])
    agent._searcher.pages[("yamz-236_rk_2014", 40)] = " ".join(["Регулировка тепловых зазоров клапанов коромысла."] * 10)
    try:
        out = a.t_prepare_ticket("Низкое давление масла", ["Проверить"], [], [{"manual_id": "yamz-236_rk_2014", "page": 40}])
    finally:
        agent._searcher.pages.clear()
    assert "error" in out and "не отправляет" in out["error"] and not conv.drafts and not stubs


def test_not_applicable_class_gives_defect_note(monkeypatch, stubs):
    monkeypatch.setattr(clients, "diagnose", lambda v, s: {
        "vehicle_id": v, "session_id": s, "status": "anomaly", "anomaly_type": "F14", "anomaly_title": "Цепь ГРМ, гидронатяжитель",
        "anomaly_score": 0.8, "confidence": 0.8, "signal_quality": "good", "description": "", "model_version": "mock-v1"})
    conv = agent.get_conversation("t-f14", "E549YT198", "S-0011")   # E549YT198 – ЯМЗ-236М2: цепи ГРМ нет
    a = agent.Agent(conv, lambda ev: None)
    a.t_search_manual(["цепь"])
    out = a.t_prepare_ticket("Цепь", ["Осмотр"], [], [{"manual_id": "yamz-236_rk_2014", "page": 40}])
    assert out.get("defect_note") and "дефектовк" in out["defect_note"] and not conv.drafts and not stubs


def test_ticket_only_on_request(stubs):
    """Черновик – только по просьбе механика: при объяснении результата инструмент отказывает, заявки нет."""
    conv = agent.get_conversation("t-req", "E549YT198", "S-0011")
    a = agent.Agent(conv, lambda ev: None)
    a.ticket_requested = False
    a.t_search_manual(["давление масла"])
    out = a.t_prepare_ticket("Низкое давление масла", ["Проверить давление"], [], [{"manual_id": "yamz-236_rk_2014", "page": 40}])
    assert "error" in out and "по просьбе механика" in out["error"] and not conv.drafts
    assert agent.TICKET_INTENT.search("Создай заявку на дефектовку по этой проверке.")
    assert not agent.TICKET_INTENT.search("Получить результат диагностики по выбранной проверке и объяснить, что делать.")


def test_reference_as_string(stubs):
    assert agent._ref("{yamz-236_rk_2014#40}") == ("yamz-236_rk_2014", 40)
    assert agent._ref({"manual_id": "yamz-236_rk_2014", "page": "41"}) == ("yamz-236_rk_2014", 41)
    assert agent._ref("мусор") == (None, 0)
