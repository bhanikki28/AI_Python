# PII Gate — Sensitive Data Redaction & Policy Gate

A locally runnable control service that inspects free text (e.g. a customer
message or an LLM prompt) **before** it is sent to an AI model, logged, or
stored. It detects synthetic Australian-banking-style PII, redacts it, and
returns a policy decision:

| Decision | Meaning |
|---|---|
| `ALLOW` | No sensitive data found — text passes unchanged |
| `REDACT` | Sensitive data found and masked — redacted text may pass |
| `BLOCK` | High-risk content or input that cannot be safely processed — fail closed |

Every decision cites the data-handling policy clause that drove it, retrieved
from a local synthetic policy corpus (RAG). The gate is exposed through a REST
API, a CLI, a small web UI and an **MCP server**, so AI clients such as Claude
Code can call it as a tool. An **optional** local LLM assistant (Ollama) only ever
sees redacted text. When Ollama isn't running, the gate degrades to
deterministic-only mode.

> Status: **Phase 0 — scaffold.** Sections below are filled in as phases land.

## Prerequisites

- Python 3.11+ (developed on 3.14)
- `make`
- Docker (optional)
- Ollama (optional — **not** required for the core path)

## Setup

```bash
cd tech_spike
make setup        # creates .venv and installs dev dependencies
```

## Run

_TBD (Phase 3)_

## Verify

```bash
make verify       # lint + tests + evals (the same checks CI runs)
```

## Evidence pack

See [evidence/](evidence/).
