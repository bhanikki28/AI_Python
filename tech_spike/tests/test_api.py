import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from pii_gate import knowledge
from pii_gate.api import create_app
from pii_gate.config import Settings

CARD = "4111 1111 1111 1111"


@pytest.fixture
def client():
    with TestClient(create_app(Settings(max_chars=500))) as c:
        yield c


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["policy_clauses"] >= 10


def test_scan_redact(client):
    res = client.post("/v1/scan", json={"text": f"card {CARD} call 0412 345 678"})
    body = res.json()
    assert res.status_code == 200
    assert body["decision"] == "REDACT"
    assert body["released_text"] == "card [CARD_NUMBER] call [PHONE_AU]"
    assert body["request_id"] == res.headers["x-request-id"]


def test_scan_block_withholds_text(client):
    body = client.post("/v1/scan", json={"text": "TFN 123 456 782"}).json()
    assert body["decision"] == "BLOCK"
    assert body["released_text"] is None


def test_empty_text_fails_closed(client):
    body = client.post("/v1/scan", json={"text": "  "}).json()
    assert body["decision"] == "BLOCK"
    assert body["reasons"][0]["code"] == "INPUT_REJECTED:EMPTY"


def test_request_id_is_propagated(client):
    res = client.post("/v1/scan", json={"text": "hello"}, headers={"x-request-id": "abc123"})
    assert res.json()["request_id"] == "abc123"
    assert res.headers["x-request-id"] == "abc123"


@pytest.mark.parametrize(
    "payload",
    [{"text": 4111111111111111}, {"txt": CARD}, [CARD]],
)
def test_invalid_request_does_not_echo_input(client, payload):
    res = client.post("/v1/scan", json=payload)
    assert res.status_code == 422
    assert res.json()["error"] == "INVALID_REQUEST"
    assert res.json()["retryable"] is False
    assert "4111" not in res.text


def test_malformed_json_does_not_echo_input(client):
    res = client.post(
        "/v1/scan", content=f'{{"text": "{CARD}"', headers={"content-type": "application/json"}
    )
    assert res.status_code == 422
    assert "4111" not in res.text


def test_oversized_body_rejected_before_parsing(client):
    res = client.post("/v1/scan", json={"text": "x" * 5000})
    assert res.status_code == 413
    assert res.json()["decision"] == "BLOCK"
    assert res.json()["retryable"] is False


def test_explain_answers_with_citations(client):
    body = client.post("/v1/explain", json={"question": "Can I log email addresses?"}).json()
    assert body["answered"]
    assert {"DH-4.1", "DH-5.1"} & {c["id"] for c in body["clauses"]}


def test_explain_abstains(client):
    body = client.post("/v1/explain", json={"question": "chocolate cake recipe"}).json()
    assert not body["answered"]
    assert body["clauses"] == []


def test_ui_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "PII Gate" in res.text


def test_ui_does_not_pass_unspread_arrays_to_dom_calls(client):
    # Regression (found in manual UI review): replaceChildren(array) renders
    # "[object HTMLDivElement]". Static guard because the UI is not browser-tested.
    html = client.get("/").text
    assert not re.search(r"^\s+(?!\.\.\.)[\w.]+\.map\(", html, re.MULTILINE)


def test_logs_contain_metadata_but_no_raw_pii(client, caplog):
    with caplog.at_level(logging.INFO, logger="pii_gate"):
        client.post("/v1/scan", json={"text": f"card {CARD} email jane@example.com"})
    scan_logs = [r for r in caplog.records if r.getMessage() == "scan"]
    assert scan_logs
    fields = scan_logs[0].fields
    assert fields["decision"] == "REDACT"
    assert fields["entity_counts"] == {"CARD_NUMBER": 1, "EMAIL": 1}
    dumped = json.dumps([getattr(r, "fields", {}) for r in caplog.records]) + caplog.text
    assert "4111" not in dumped
    assert "jane@example.com" not in dumped


def test_not_ready_when_policy_corpus_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("PII_GATE_POLICY_DIR", str(tmp_path))
    try:
        with TestClient(create_app(Settings())) as c:
            assert c.get("/health").status_code == 503
            res = c.post("/v1/scan", json={"text": "hello"})
            assert res.status_code == 503
            assert res.json()["decision"] == "BLOCK"
            assert res.json()["retryable"] is True  # system error: safe to retry later
            assert res.headers["retry-after"] == "30"
    finally:
        knowledge.default_index.cache_clear()
