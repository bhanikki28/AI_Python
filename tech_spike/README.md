# PII Gate: sensitive-data redaction and policy gate

A locally runnable control service that inspects free text, such as a customer complaint or an LLM prompt, **before** it reaches an AI model, a log or storage. It detects Australian banking-style PII, redacts it, and returns a decision that cites the data-handling policy clause behind it.

| Decision | Meaning |
|---|---|
| `ALLOW` | Nothing sensitive found. Text passes unchanged. |
| `REDACT` | Sensitive data masked (`[CARD_NUMBER]`, `[EMAIL]`, …). The redacted text may pass. |
| `BLOCK` | High-risk data (TFN, Medicare, bulk extract) or input that can't be safely inspected. **Nothing is released.** |

**Detected:** card numbers (Luhn), TFN, ABN, Medicare (checksums), BSB and account numbers (context keywords), emails, AU phone numbers, plus a fail-safe for unclassified long numbers.

**Agentic features:**
- **RAG**: policy Q&A and citations, abstaining when nothing is relevant.
- **MCP server**: the gate as a tool for AI agents.
- **Optional local-LLM assistant** (Ollama): sees only redacted text, and its output is re-verified by the gate. It degrades gracefully when Ollama isn't installed.

All data is **synthetic**. No API keys, credentials or network services are needed for the core path.

## Prerequisites

- Python 3.11+ (developed on 3.14; CI runs 3.11 and 3.13)
- `make`
- Optional: Docker, for the container path; Ollama, for the LLM assistant only

## Setup, run and verify

```bash
cd tech_spike
make setup        # create .venv and install dependencies
make verify       # lint + 129 tests + evals: the same checks CI runs
make run          # API + web UI at http://127.0.0.1:8000  (OpenAPI docs: /docs)
```

| Command | What it does |
|---|---|
| `make eval` | eval suite only; report written to `reports/eval-report.md` |
| `make mcp-demo` | scripted MCP client: starts the MCP server over stdio and calls its tools |
| `make audit` | dependency vulnerability scan (pip-audit) |
| `make docker-smoke` | build the container and smoke-test it over HTTP |
| `docker compose up --build` | run in a container (add `--profile llm` for Ollama) |

## Example

```bash
curl -s -X POST localhost:8000/v1/scan -H 'content-type: application/json' \
  -d '{"text":"Hi, card 4111 1111 1111 1111 charged twice, call 0412 345 678"}'
```
```json
{
  "request_id": "7ae4a9fc…",
  "decision": "REDACT",
  "released_text": "Hi, card [CARD_NUMBER] charged twice, call [PHONE_AU]",
  "findings": [
    {"type": "CARD_NUMBER", "start": 9, "end": 28, "method": "checksum"},
    {"type": "PHONE_AU", "start": 49, "end": 61, "method": "pattern"}
  ],
  "reasons": [
    {"code": "ENTITY_DETECTED", "decision": "REDACT", "entity_type": "CARD_NUMBER", "count": 1,
     "policy": {"id": "DH-2.1", "title": "Payment card numbers", "text": "Payment card numbers (PAN, …) must never be sent to AI models…"}},
    …
  ]
}
```

`"My TFN is 123 456 782"` returns `"decision": "BLOCK"`, `"released_text": null`, citing DH-3.1.

CLI: `.venv/bin/pii-gate scan "…"` exits 0 if the text is safe to use and 2 on BLOCK. `pii-gate explain "…"` and `pii-gate assist "…"` are also available.

## Five-minute demo script

1. **UI** (`make run`, open http://127.0.0.1:8000). Click the samples in turn:
   - **Card + phone**: REDACT, with policy citations.
   - **TFN**: BLOCK, text withheld.
   - **Bulk export**: BLOCK under DH-6.1.
   - **Clean**: ALLOW.
   - **Evasion**: zero-width and full-width digits are still caught.
2. **Ask the policy:** "Can I put email addresses in logs?" gets cited clauses. "chocolate cake recipe" is declined, with a referral to the Privacy Office.
3. **Summarise (optional LLM):** without Ollama it shows `degraded`, the step table, and the gate result still returned.
4. **MCP:** `make mcp-demo`, which is an agent-style tool-calling session with no LLM needed.
5. **Evidence of safety:** `make verify` (watch `leak_rate 0.000`), then point to the logs in the `make run` terminal. They contain types and counts, never values.

## MCP server (tool calling from AI agents)

The server exposes three read-only tools: `scan_text`, `redact_text` and `explain_policy`. Its instructions tell the agent to scan text before using it and to honour BLOCK.

```bash
# Claude Code CLI
claude mcp add pii-gate -- "$(pwd)/.venv/bin/pii-gate-mcp"
```
```json
// Claude Desktop / Cursor / .mcp.json
{ "mcpServers": { "pii-gate": { "command": "/ABSOLUTE/PATH/tech_spike/.venv/bin/pii-gate-mcp" } } }
```

## Optional: local LLM assistant (Ollama)

**Not required.** Without Ollama, `/v1/assist` returns `"status": "degraded"` along with the normal gate result.

The pipeline:
1. The **gate** scans the input. On BLOCK, the LLM is never called.
2. The **local model** sees only redacted text and returns summary, category and urgency as JSON.
3. The **verifier** validates the JSON and re-scans the output.

To try it: install Ollama, run `ollama pull llama3.2:3b`, then `make run`.

## Configuration

Environment variables only; validated at startup; no secrets required. See [.env.example](.env.example) and [evidence/operate.md](evidence/operate.md).

## Project layout

```text
src/pii_gate/     validation, checksums, detectors, redactor, policy, knowledge (RAG), gate,
                  api, cli, mcp_server, assistant, config, logging_setup, static/index.html
policies/         synthetic data-handling standard (15 clauses, cited by ID)
tests/            129 unit/integration tests
evals/            dataset generator, metrics, eval runner (thresholds gate CI)
sample-data/      eval_cases.jsonl (69 labelled cases), policy_questions.jsonl (24)
examples/         mcp_demo.py
scripts/          smoke_test.sh (container smoke test)
evidence/         intent, design, agentic-workflow, verify, operate, decisions
../.github/workflows/pii-gate.yml   CI (repo root, path-filtered to tech_spike/**)
```

## Known limitations

- **Names, street addresses and dates of birth are not detected.** This needs NER; the evals report it as a known gap (4 of 4 probes missed).
- **Evals use synthetic data** built from the targeted formats. The 1.000 scores show the design works and catch regressions; they are not a real-world accuracy estimate.
- **The LLM assistant has not been run against a real model**; its tests use a fake Ollama. If a small model breaks the JSON format, the result fails closed (`invalid_output`).
- **Conservative by design.** Overlaps take the stricter label and unknown long numbers are redacted, so some benign numbers will be over-redacted.
- English only; text only; no authN, authZ or rate limiting (expected at the API gateway in production).

## Evidence pack

| File | Contents |
|---|---|
| [intent.md](evidence/intent.md) | problem, users, assumptions, scope, success criteria |
| [design.md](evidence/design.md) | architecture, data flow, trade-offs, security, cloud shape |
| [agentic-workflow.md](evidence/agentic-workflow.md) | how Claude Code was steered and reviewed; what it got wrong |
| [verify.md](evidence/verify.md) | test and eval results, CI evidence, check matrix, gaps |
| [operate.md](evidence/operate.md) | run, logs, config, failure modes, rollback, local to cloud |
| [decisions.md](evidence/decisions.md) | 5 decision records and what was not built |

## Submission notes

- **AI coding agent:** Claude Code (VS Code extension), Claude Opus 5.5 (session started on Sonnet 5.5).
- **Time spent:** <!-- TODO(candidate): fill in --> about __ h __ min build, plus __ min packaging.
- **No setup beyond this README** is needed for the core path.
