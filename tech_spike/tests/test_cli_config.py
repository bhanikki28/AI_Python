import json

import pytest

from pii_gate.cli import EXIT_BLOCK, main
from pii_gate.config import ConfigError, load_settings


def test_cli_scan_redact(capsys):
    assert main(["scan", "email me at a.b@example.com"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "REDACT"
    assert out["released_text"] == "email me at [EMAIL]"


def test_cli_scan_block_exit_code(capsys):
    assert main(["scan", "TFN 123 456 782"]) == EXIT_BLOCK
    assert json.loads(capsys.readouterr().out)["decision"] == "BLOCK"


def test_cli_scan_file(tmp_path, capsys):
    path = tmp_path / "msg.txt"
    path.write_text("call 0412 345 678", encoding="utf-8")
    assert main(["scan", "--file", str(path)]) == 0
    assert "[PHONE_AU]" in capsys.readouterr().out


def test_cli_explain(capsys):
    assert main(["explain", "what about tax file numbers?"]) == 0
    assert json.loads(capsys.readouterr().out)["clauses"][0]["id"] == "DH-3.1"


def test_cli_bad_config(monkeypatch, capsys):
    monkeypatch.setenv("PII_GATE_MAX_CHARS", "lots")
    assert main(["scan", "hello"]) == 1
    assert "PII_GATE_MAX_CHARS" in capsys.readouterr().err


def test_settings_defaults():
    s = load_settings({})
    assert (s.max_chars, s.log_level, s.port) == (10_000, "INFO", 8000)
    assert s.llm_max_attempts == 3


@pytest.mark.parametrize(
    "env",
    [
        {"PII_GATE_MAX_CHARS": "0"},
        {"PII_GATE_MAX_CHARS": "abc"},
        {"PII_GATE_PORT": "70000"},
        {"PII_GATE_LOG_LEVEL": "LOUD"},
        {"PII_GATE_LLM_MAX_ATTEMPTS": "0"},
        {"PII_GATE_LLM_MAX_ATTEMPTS": "10"},
    ],
)
def test_invalid_settings_fail_fast(env):
    with pytest.raises(ConfigError):
        load_settings(env)
