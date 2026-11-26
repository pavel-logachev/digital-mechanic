"""Заявка уходит в ТОиР только через confirm_ticket (кнопка механика), с проверкой полей кодом."""
import pytest

from app import agent, clients


class StubSearcher:
    def search(self, q, engine, k=5, rewrites=None):
        return [{"manual_id": "yamz-236_rk_2014", "page": 40, "score": 1, "text": "затяжка болтов крышек коренных подшипников", "snippet": ""}]

    def page_text(self, m, p):
        return "текст"


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
