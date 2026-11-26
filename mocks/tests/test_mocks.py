import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mock_ml.app import app as ml_app  # noqa: E402
from mock_toir.app import app as toir_app  # noqa: E402

FIELDS = ["vehicle_id", "session_id", "status", "anomaly_type", "anomaly_title", "anomaly_score",
          "confidence", "signal_quality", "description", "model_version"]

with open(os.path.join(ROOT, "data", "vehicles.json"), encoding="utf-8") as f:
    DATA = json.load(f)
ALL = [(v["vehicle_id"], s) for v in DATA["vehicles"] for s in v["sessions"]]

ml = TestClient(ml_app)
toir = TestClient(toir_app)


def first(status):
    return next((vid, s) for vid, s in ALL if s["status"] == status)


def test_health():
    r = ml.get("/health")
    assert r.status_code == 200 and r.json()["vehicles"] == 50
    assert toir.get("/health").status_code == 200


def test_every_session_matches_data():
    for vid, s in ALL:
        r = ml.post("/diagnose", json={"vehicle_id": vid, "session_id": s["session_id"]})
        assert r.status_code == 200, (vid, s["session_id"])
        body = r.json()
        assert list(body.keys()) == FIELDS
        assert body == {k: s[k] for k in FIELDS}


def test_normal_has_no_fault():
    vid, s = first("normal")
    body = ml.post("/diagnose", json={"vehicle_id": vid, "session_id": s["session_id"]}).json()
    assert body["anomaly_type"] is None and body["anomaly_title"] is None
    assert body["anomaly_score"] is not None and body["confidence"] is not None


def test_anomaly_has_fault_and_scores():
    vid, s = first("anomaly")
    body = ml.post("/diagnose", json={"vehicle_id": vid, "session_id": s["session_id"]}).json()
    assert body["anomaly_type"][0] == "F" and body["anomaly_title"]
    assert 0 <= body["anomaly_score"] <= 1 and 0 <= body["confidence"] <= 1


def test_check_failed_is_empty():
    vid, s = first("check_failed")
    body = ml.post("/diagnose", json={"vehicle_id": vid, "session_id": s["session_id"]}).json()
    for k in ("anomaly_type", "anomaly_title", "anomaly_score", "confidence"):
        assert body[k] is None
    assert body["signal_quality"] == "bad"


def test_cors_preflight():
    headers = {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST",
               "Access-Control-Request-Headers": "content-type"}
    for client, path in ((ml, "/diagnose"), (toir, "/tickets")):
        r = client.options(path, headers=headers)
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "*"


def test_openapi_example_exists():
    ex = ml_app.openapi()["components"]["schemas"]["DiagnoseRequest"]["properties"]
    vid, sid = ex["vehicle_id"]["examples"][0], ex["session_id"]["examples"][0]
    assert ml.post("/diagnose", json={"vehicle_id": vid, "session_id": sid}).status_code == 200


def test_unknown_ids():
    vid, s = ALL[0]
    assert ml.post("/diagnose", json={"vehicle_id": "NOPE", "session_id": s["session_id"]}).status_code == 404
    assert ml.post("/diagnose", json={"vehicle_id": vid, "session_id": "S-9999"}).status_code == 404
    other = next(x for v, x in ALL if v != vid)
    assert ml.post("/diagnose", json={"vehicle_id": vid, "session_id": other["session_id"]}).status_code == 404


def test_diagnose_validation():
    assert ml.post("/diagnose", json={"vehicle_id": "A"}).status_code == 422
    assert ml.post("/diagnose", json={}).status_code == 422


def ticket(**over):
    vid, s = first("anomaly")
    body = {"vehicle_id": vid, "session_id": s["session_id"], "anomaly_type": s["anomaly_type"],
            "conclusion": "Проверка по руководству", "urgency": "medium",
            "operations": ["Проверить натяжение ремня"], "spare_parts": [],
            "references": [{"manual": "Руководство", "pdf_page": 28}]}
    body.update(over)
    return body


def test_tickets_are_numbered():
    r1 = toir.post("/tickets", json=ticket())
    r2 = toir.post("/tickets", json=ticket(urgency="high"))
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["status"] == "created"
    n1, n2 = int(r1.json()["ticket_id"][4:]), int(r2.json()["ticket_id"][4:])
    assert r1.json()["ticket_id"].startswith("TKT-") and len(r1.json()["ticket_id"]) == 8
    assert n2 == n1 + 1


@pytest.mark.parametrize("over", [
    {"urgency": "urgent"},
    {"anomaly_type": "RAG-03"},
    {"anomaly_type": "F15"},
    {"operations": []},
    {"references": []},
    {"references": [28]},
    {"references": [{"manual": "Руководство", "pdf_page": 0}]},
    {"conclusion": ""},
])
def test_ticket_validation(over):
    assert toir.post("/tickets", json=ticket(**over)).status_code == 422


def test_ticket_missing_field():
    body = ticket()
    del body["spare_parts"]
    assert toir.post("/tickets", json=body).status_code == 422


def test_ticket_unknown_ids():
    assert toir.post("/tickets", json=ticket(vehicle_id="NOPE")).status_code == 404
    assert toir.post("/tickets", json=ticket(session_id="S-9999")).status_code == 404
