from pii_gate import detectors, gate
from pii_gate.policy import Decision


def test_clean_text_allowed_unchanged():
    result = gate.scan("The branch was closed on Tuesday.")
    assert result.decision == Decision.ALLOW
    assert result.released_text == "The branch was closed on Tuesday."


def test_redact_path_end_to_end():
    result = gate.scan("Card 4111 1111 1111 1111 charged twice, call 0412 345 678")
    assert result.decision == Decision.REDACT
    assert result.released_text == "Card [CARD_NUMBER] charged twice, call [PHONE_AU]"
    body = result.to_dict()
    assert body["decision"] == "REDACT"
    assert {r["policy"]["id"] for r in body["reasons"]} == {"DH-2.1", "DH-4.1"}
    assert body["reasons"][0]["policy"]["title"]


def test_block_path_withholds_text():
    result = gate.scan("My TFN is 123 456 782 and email a@example.com")
    assert result.decision == Decision.BLOCK
    assert result.released_text is None
    assert result.to_dict()["reasons"][0]["policy"]["id"] == "DH-3.1"


def test_invalid_input_fails_closed():
    result = gate.scan("x" * 50, max_chars=10)
    assert result.decision == Decision.BLOCK
    assert result.released_text is None
    assert result.reasons[0].code == "INPUT_REJECTED:TOO_LARGE"


def test_engine_error_fails_closed(monkeypatch):
    def boom(_text):
        raise RuntimeError("detector crashed")

    monkeypatch.setattr(detectors, "detect", boom)
    result = gate.scan("Card 4111 1111 1111 1111")
    assert result.decision == Decision.BLOCK
    assert result.released_text is None
    assert result.reasons[0].code == "ENGINE_ERROR"


def test_response_never_contains_raw_pii():
    raw = "4111 1111 1111 1111"
    body = str(gate.scan(f"card {raw} and tfn 123 456 782").to_dict())
    assert raw not in body
    assert "123 456 782" not in body
