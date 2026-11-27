"""Надежность для работы в автопарке: сбои внешних сервисов, перезапуск, двойное нажатие."""
import threading
from typing import ClassVar

import httpx
import pytest
from openai import APIConnectionError


def test_ml_retries_on_server_error_but_ticket_is_not_repeated(monkeypatch):
    from app import clients
    calls = {"diagnose": 0, "tickets": 0}

    def fake_post(url, json, timeout):
        req = httpx.Request("POST", url)
        if url.endswith("/diagnose"):
            calls["diagnose"] += 1
            if calls["diagnose"] == 1:
                return httpx.Response(503, request=req)
            return httpx.Response(200, json={"vehicle_id": "A", "session_id": "S"}, request=req)
        calls["tickets"] += 1
        raise httpx.ReadTimeout("timeout", request=req)  # запрос мог дойти – повторять нельзя

    monkeypatch.setattr(clients.httpx, "post", fake_post)
    monkeypatch.setattr(clients.time, "sleep", lambda s: None)
    assert clients.diagnose("A", "S")["session_id"] == "S"
    assert calls["diagnose"] == 2
    with pytest.raises(clients.ServiceError):
        clients.create_ticket({"vehicle_id": "A"})
    assert calls["tickets"] == 1


def test_ticket_retried_only_when_connection_failed(monkeypatch):
    from app import clients
    calls = []

    def fake_post(url, json, timeout):
        req = httpx.Request("POST", url)
        calls.append(url)
        if len(calls) == 1:
            raise httpx.ConnectError("refused", request=req)  # сервис запрос точно не получил
        return httpx.Response(201, json={"ticket_id": "TKT-1", "status": "created"}, request=req)

    monkeypatch.setattr(clients.httpx, "post", fake_post)
    monkeypatch.setattr(clients.time, "sleep", lambda s: None)
    assert clients.create_ticket({})["ticket_id"] == "TKT-1"
    assert len(calls) == 2


def test_llm_falls_back_to_reserve_model(monkeypatch):
    from app import config, llm

    class Broken:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    raise APIConnectionError(request=httpx.Request("POST", "https://api.deepseek.com"))

    class Msg:
        content, tool_calls = "ответ", None

    class Resp:
        choices: ClassVar[list] = [type("C", (), {"message": Msg})]
        usage = None

    seen = {}

    class Reserve:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    seen.update(kw)
                    return Resp

    monkeypatch.setattr(llm, "client", lambda: Broken)
    monkeypatch.setattr(llm, "fallback_client", lambda: Reserve)
    usage = llm.Usage()
    assert llm.chat([{"role": "user", "content": "?"}], usage=usage).content == "ответ"
    assert seen["model"] == config.LLM_FALLBACK_MODEL and "extra_body" not in seen
    assert usage.fallback is True


def test_conversation_and_draft_survive_restart(tmp_path, monkeypatch):
    from app import agent, config
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    c = agent.Conversation("conv-1", "A123BC77", "S-1")
    c.messages.append({"role": "user", "content": "вопрос"})
    c.drafts["D-1"] = {"vehicle_id": "A123BC77"}
    c.seen.add(("yamz-236_re_2010", 19))
    agent.save_conversation(c)
    monkeypatch.setattr(agent, "_convs", {})  # «перезапуск»: память процесса пуста
    again = agent.get_conversation("conv-1", "A123BC77", "S-1")
    assert again.messages == c.messages and ("yamz-236_re_2010", 19) in again.seen
    monkeypatch.setattr(agent, "_convs", {})
    found = agent.find_draft("D-1")
    assert found and found[0].id == "conv-1"


def test_double_click_creates_one_ticket(monkeypatch):
    from app import agent, clients, data
    conv = agent.Conversation("conv-2", "A", "S")
    conv.drafts["D-2"] = {"vehicle_id": "A", "session_id": "S", "anomaly_type": "F02", "conclusion": "x", "urgency": "high",
                          "operations": ["работа"], "spare_parts": [], "references": [{"manual": "m", "pdf_page": 1}]}
    monkeypatch.setattr(agent, "_convs", {"conv-2": conv})
    monkeypatch.setattr(agent, "save_conversation", lambda c: None)
    monkeypatch.setattr(data, "add_ticket", lambda t: None)
    created = []
    gate = threading.Event()

    def slow_ticket(payload):
        gate.wait(1)
        created.append(payload)
        return {"ticket_id": f"TKT-{len(created)}", "status": "created"}

    monkeypatch.setattr(clients, "create_ticket", slow_ticket)
    results = []
    threads = [threading.Thread(target=lambda: results.append(agent.confirm_ticket("D-2", {}))) for _ in range(2)]
    for t in threads:
        t.start()
    gate.set()
    for t in threads:
        t.join()
    assert len(created) == 1
    assert {r["ticket_id"] for r in results} == {"TKT-1"}


def test_audit_rotates_by_month_and_keeps_text_only(tmp_path, monkeypatch):
    from app import audit, config
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    audit.write("voice", text="какое давление масла", bytes=1000)
    files = list((tmp_path / "audit").glob("*.jsonl"))
    assert len(files) == 1
    line = files[0].read_text(encoding="utf-8")
    assert "какое давление масла" in line and "audio" not in line


def test_security_headers(monkeypatch):
    from fastapi.testclient import TestClient

    from app import clients, main
    monkeypatch.setattr(clients, "health", lambda: {"ml": True, "toir": True})
    r = TestClient(main.app).get("/api/health")
    assert r.status_code == 200
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"


def test_users_roles_and_sessions(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import config, data, main, users
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(config, "USERS_FILE", tmp_path / "users.json")
    users.save([{"login": "petrov", "name": "Петров П.", "role": "mechanic", "password": users.hash_password("секрет-123")},
                {"login": "sidorov", "name": "Сидоров С.", "role": "chief", "password": users.hash_password("главный-123")}])
    monkeypatch.setattr(data, "fleet", lambda: {"ok": True})
    c = TestClient(main.app)
    assert c.get("/api/vehicles").status_code == 401
    assert "Логин" in c.get("/").text
    assert c.post("/api/login", json={"login": "petrov", "password": "не тот"}).status_code == 401
    assert c.post("/api/login", json={"login": "Petrov", "password": "секрет-123"}).status_code == 200
    assert c.get("/api/me").json()["user"]["role"] == "mechanic"
    assert c.get("/api/fleet").status_code == 403  # сводка парка – только главному механику
    chief = TestClient(main.app)
    chief.post("/api/login", json={"login": "sidorov", "password": "главный-123"})
    assert chief.get("/api/fleet").json() == {"ok": True}
    assert users.from_session("подделка.abc") is None
    assert "секрет" not in (tmp_path / "users.json").read_text(encoding="utf-8")


def test_doubtful_signal_ticket_needs_confirmed_inspection(monkeypatch):
    from app import agent, clients, data
    conv = agent.Conversation("conv-3", "A", "S")
    conv.drafts["D-3"] = {"vehicle_id": "A", "session_id": "S", "anomaly_type": "F01", "conclusion": "x", "urgency": "medium",
                          "operations": ["осмотр"], "spare_parts": [], "references": [{"manual": "m", "pdf_page": 1}],
                          "needs_inspection": True}
    monkeypatch.setattr(agent, "_convs", {"conv-3": conv})
    monkeypatch.setattr(agent, "save_conversation", lambda c: None)
    saved = []
    monkeypatch.setattr(data, "add_ticket", saved.append)
    monkeypatch.setattr(clients, "create_ticket", lambda p: {"ticket_id": "TKT-9", "status": "created"})
    with pytest.raises(ValueError):
        agent.confirm_ticket("D-3", {})  # без отметки об осмотре сервер заявку не пропускает, даже в обход интерфейса
    assert agent.confirm_ticket("D-3", {"inspection_confirmed": True})["ticket_id"] == "TKT-9"
    assert saved[0]["inspection_confirmed"] is True


def test_demo_video_open_even_with_login(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import config, main, users
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(users, "enabled", lambda: True)
    c = TestClient(main.app)
    assert c.get("/demo.mp4").status_code == 404
    (tmp_path / "public").mkdir()
    (tmp_path / "public" / "demo.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    r = c.get("/demo.mp4")
    assert r.status_code == 200 and r.headers["content-type"] == "video/mp4"
    assert c.get("/api/vehicles").status_code == 401  # остальное по-прежнему за входом


def test_changed_priority_needs_reason_and_reason_reaches_toir(monkeypatch):
    """#111: механик вправе изменить приоритет программы, но сервер требует причину – даже в обход интерфейса."""
    from app import agent, clients, data
    conv = agent.Conversation("conv-4", "A", "S")
    conv.drafts["D-4"] = {"vehicle_id": "A", "session_id": "S", "anomaly_type": "F04", "conclusion": "Износ ремня", "urgency": "medium",
                          "operations": ["осмотр ремня"], "spare_parts": [], "references": [{"manual": "m", "pdf_page": 1}]}
    monkeypatch.setattr(agent, "_convs", {"conv-4": conv})
    monkeypatch.setattr(agent, "save_conversation", lambda c: None)
    saved, sent = [], []
    monkeypatch.setattr(data, "add_ticket", saved.append)
    monkeypatch.setattr(clients, "create_ticket", lambda p: sent.append(p) or {"ticket_id": "TKT-7", "status": "created"})
    with pytest.raises(ValueError, match="причину"):
        agent.confirm_ticket("D-4", {"urgency": "high"})
    with pytest.raises(ValueError, match="Приоритет"):
        agent.confirm_ticket("D-4", {"urgency": "срочно", "urgency_reason": "x"})
    assert not sent
    agent.confirm_ticket("D-4", {"urgency": "high", "urgency_reason": "Ремень с трещинами при осмотре"})
    assert sent[0]["urgency"] == "high"
    assert sent[0]["conclusion"] == "Износ ремня\nПричина изменения приоритета: Ремень с трещинами при осмотре"
    assert saved[0]["urgency_changed_by_mechanic"] is True and saved[0]["urgency_reason"] == "Ремень с трещинами при осмотре"


def test_rate_limit_window_and_total(monkeypatch):
    from app import main
    now = [1000.0]
    monkeypatch.setattr(main.time, "monotonic", lambda: now[0])
    rl = main.RateLimit(per_key=2, window=60, total=3, total_window=100)
    for ip in ("a", "a", "b"):
        assert not rl.blocked(ip)
        rl.hit(ip)
    assert rl.blocked("a")          # лимит адреса
    assert rl.blocked("c")          # общий лимит
    now[0] += 61
    assert rl.blocked("a")          # окно адреса прошло, но общий лимит еще в своем окне
    now[0] += 40
    assert not rl.blocked("a") and not rl.blocked("c")
    rl2 = main.RateLimit(per_key=2, window=60)
    rl2.hit("x")
    rl2.hit("x")
    assert rl2.blocked("x") and not rl2.blocked("y")


def test_ticket_journal_written_atomically(tmp_path, monkeypatch):
    from app import config, data
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    data.add_ticket({"ticket_id": "TKT-1", "vehicle_id": "A", "session_id": "S"})
    data.add_ticket({"ticket_id": "TKT-2", "vehicle_id": "B", "session_id": "S2"})
    assert [t["ticket_id"] for t in data.tickets()] == ["TKT-1", "TKT-2"]
    assert [t["ticket_id"] for t in data.tickets("B")] == ["TKT-2"]
    assert not list(tmp_path.glob("*.tmp"))


def test_conversations_in_memory_are_bounded(monkeypatch):
    from app import agent
    monkeypatch.setattr(agent, "_convs", {})
    monkeypatch.setattr(agent, "MAX_CONVS_IN_MEMORY", 3)
    monkeypatch.setattr(agent, "_load_conversation", lambda cid: None)
    for i in range(5):
        agent.get_conversation(f"c{i}", "A", "S")
    agent.get_conversation("c2", "A", "S")      # обращение поднимает разговор в конец очереди
    assert list(agent._convs) == ["c3", "c4", "c2"]


def test_manual_pages_only_from_this_conversation(tmp_path, monkeypatch):
    """Открытый стенд не раздает руководство целиком: только страницы, найденные помощником в разговоре."""
    from fastapi.testclient import TestClient

    from app import agent, config, main
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    conv = agent.Conversation("conv-p", "A", "S")
    conv.seen.update({("yamz-236_re_2010", 19), ("yamz-236_re_2010", 41)})
    monkeypatch.setattr(agent, "_convs", {"conv-p": conv})

    class Pages:
        def page_text(self, manual_id, page):
            return f"страница {page}"

    monkeypatch.setattr(agent, "searcher", Pages)
    c = TestClient(main.app)
    ok = c.get("/api/manuals/yamz-236_re_2010/pages/19", params={"conversation_id": "conv-p"}).json()
    assert ok["text"] == "страница 19" and ok["prev"] is None and ok["next"] == 41
    assert c.get("/api/manuals/yamz-236_re_2010/pages/20", params={"conversation_id": "conv-p"}).status_code == 403
    assert c.get("/api/manuals/yamz-236_re_2010/pages/19").status_code == 403
    assert c.get("/api/manuals/yamz-236_re_2010/pages/19.png", params={"conversation_id": "чужой"}).status_code == 403
