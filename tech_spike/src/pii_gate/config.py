"""Configuration from environment variables, validated at startup (fail fast on bad config).

No secrets are needed for the core path. See .env.example for the full list.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from pii_gate.validation import DEFAULT_MAX_CHARS

LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    max_chars: int = DEFAULT_MAX_CHARS
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    # Optional local LLM assistant. Empty URL disables it entirely.
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    llm_timeout_s: int = 30

    @property
    def max_body_bytes(self) -> int:
        # Worst case 4 bytes per UTF-8 character plus JSON overhead.
        return self.max_chars * 4 + 1024


def _int(env: Mapping[str, str], name: str, default: int, low: int, high: int) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer") from None
    if not low <= value <= high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return value


def load_settings(env: Mapping[str, str] = os.environ) -> Settings:
    log_level = env.get("PII_GATE_LOG_LEVEL", "INFO").upper()
    if log_level not in LOG_LEVELS:
        raise ConfigError(f"PII_GATE_LOG_LEVEL must be one of {sorted(LOG_LEVELS)}")
    ollama_url = env.get("PII_GATE_OLLAMA_URL", Settings.ollama_url).rstrip("/")
    if ollama_url and not ollama_url.startswith(("http://", "https://")):
        raise ConfigError("PII_GATE_OLLAMA_URL must start with http:// or https:// (or be empty)")
    return Settings(
        max_chars=_int(env, "PII_GATE_MAX_CHARS", DEFAULT_MAX_CHARS, 1, 100_000),
        log_level=log_level,
        host=env.get("PII_GATE_HOST", "127.0.0.1"),
        port=_int(env, "PII_GATE_PORT", 8000, 1, 65_535),
        ollama_url=ollama_url,
        ollama_model=env.get("PII_GATE_OLLAMA_MODEL", Settings.ollama_model),
        llm_timeout_s=_int(env, "PII_GATE_LLM_TIMEOUT", Settings.llm_timeout_s, 1, 300),
    )
