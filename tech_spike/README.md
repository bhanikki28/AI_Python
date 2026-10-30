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

```bash
make run          # API + web UI on http://127.0.0.1:8000  (API docs: /docs)
```

Web UI: open http://127.0.0.1:8000 and click a sample (Card + phone, TFN, Bulk, Clean, Evasion).

API:
```bash
curl -s -X POST localhost:8000/v1/scan -H 'content-type: application/json' \
  -d '{"text":"Hi, card 4111 1111 1111 1111 charged twice, call 0412 345 678"}'
# -> {"decision":"REDACT","released_text":"Hi, card [CARD_NUMBER] charged twice, call [PHONE_AU]", ...}

curl -s -X POST localhost:8000/v1/explain -H 'content-type: application/json' \
  -d '{"question":"Can I put email addresses in logs?"}'
```

CLI (exit code 0 = ALLOW/REDACT, 2 = BLOCK):
```bash
.venv/bin/pii-gate scan "My TFN is 123 456 782"
.venv/bin/pii-gate scan --file message.txt
.venv/bin/pii-gate explain "What do I do with a Medicare number?"
```

Configuration is via environment variables. See [.env.example](.env.example). No secrets are needed.

### MCP server (tool calling from AI agents)

The gate is also an MCP server with three read-only tools: `scan_text`, `redact_text` and
`explain_policy`. Its server instructions tell the agent to scan text before using it
and to honour BLOCK.

```bash
make mcp-demo     # scripted MCP client: launches the server over stdio and calls each tool
```

Register it with an MCP client, using an absolute path to the venv executable:

```bash
# Claude Code CLI
claude mcp add pii-gate -- "$(pwd)/.venv/bin/pii-gate-mcp"
```

```json
// Claude Desktop / Cursor / Claude Code .mcp.json
{ "mcpServers": { "pii-gate": { "command": "/ABSOLUTE/PATH/tech_spike/.venv/bin/pii-gate-mcp" } } }
```

Then ask the agent, for example: *"Use pii-gate to check this complaint before you summarise
it: my card 4111 1111 1111 1111 was charged twice."*

### Optional: local LLM complaint assistant (Ollama)

**Not required.** Without Ollama, `/v1/assist` and `pii-gate assist` return
`"status": "degraded"` along with the normal gate result.

The pipeline has three steps:
1. The gate scans the input. On BLOCK, the LLM is never called.
2. A local model receives **only the redacted text** and returns a summary, category and urgency as JSON.
3. A verifier checks that JSON and re-scans the summary. Any PII the model produced is redacted or withheld.

To try it with a model:
```bash
# install from https://ollama.com, then:
ollama pull llama3.2:3b
make run          # the "Summarise" panel in the UI now shows "assistant available"
.venv/bin/pii-gate assist "My card 4111 1111 1111 1111 was charged twice, please refund"
```

## Verify

```bash
make verify       # lint + tests + evals (the same checks CI runs)
```

## Evidence pack

See [evidence/](evidence/).
