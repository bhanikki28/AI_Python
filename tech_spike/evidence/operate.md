# Operate

## Run

| Mode | Command |
|---|---|
| API + UI (local) | `make run`, then http://127.0.0.1:8000 (OpenAPI docs at `/docs`) |
| Container | `make docker-run` or `docker compose up --build` |
| Container + Ollama | `docker compose --profile llm up --build`, then `docker compose exec ollama ollama pull llama3.2:3b` |
| MCP server (stdio) | `make mcp`, or register `.venv/bin/pii-gate-mcp` with an MCP client |
| CLI | `.venv/bin/pii-gate scan "…"`: exit 0 means text is safe to use, 2 means BLOCK |

## Status and logs

- `GET /health` returns `status`, `version`, `policy_clauses`, `max_chars` and `assistant` (`available` / `unavailable` / `disabled`).
  - **503** means not ready: the policy corpus failed to load, or a rule cites a missing clause. Every scan then returns 503 with `BLOCK`.
  - `assistant: unavailable` does **not** make the service unready.
- The Docker `HEALTHCHECK` polls `/health`.
- Logs are **one JSON object per line on stderr**, never containing input text or matched values (policy DH-5.1):

```json
{"ts": "...", "level": "INFO", "event": "scan", "request_id": "7ae4…", "decision": "REDACT",
 "input_chars": 61, "entity_counts": {"CARD_NUMBER": 1, "PHONE_AU": 1}, "reason_codes": ["ENTITY_DETECTED"]}
```

| Event | Meaning |
|---|---|
| `request` | every HTTP request: method, path, status, latency_ms |
| `scan`, `explain`, `assist_request` | outcome metadata per call |
| `tool_call` | MCP tool calls |
| `engine_error`, `unhandled_error`, `startup_failed` | fail-closed paths: exception **type** only |
| `llm_retry` | a transient LLM failure, retried: attempt, error_type, delay_s |
| `llm_unavailable` | assistant degraded: error_type, `retryable`, attempts |
| `llm_invalid_output` | LLM reply rejected by the verifier (not retried) |

Use `X-Request-ID` on requests to correlate with upstream services. It's echoed in the response and the logs.

## Configuration and secrets

All settings come from environment variables and are validated at startup; invalid values stop the process with a clear message. See [.env.example](../.env.example).

| Variable | Default | Notes |
|---|---|---|
| `PII_GATE_MAX_CHARS` | 10000 | 1–100000; larger input is BLOCKed, and oversized bodies get 413 |
| `PII_GATE_LOG_LEVEL` | INFO | DEBUG / INFO / WARNING / ERROR |
| `PII_GATE_HOST` / `PII_GATE_PORT` | 127.0.0.1 / 8000 | the container uses 0.0.0.0 |
| `PII_GATE_POLICY_DIR` | repo `policies/` | the container sets `/app/policies` |
| `PII_GATE_OLLAMA_URL` | http://127.0.0.1:11434 | **empty disables the assistant** (kill switch) |
| `PII_GATE_OLLAMA_MODEL` / `PII_GATE_LLM_TIMEOUT` | llama3.2:3b / 30 s | the timeout is the overall budget, retries included |
| `PII_GATE_LLM_MAX_ATTEMPTS` | 3 | 1–5; transient LLM failures only; `1` disables retries |

**Secrets:** none are needed for any path. In the cloud, an LLM endpoint credential would come from the platform secrets manager, injected at runtime, and never from env files or images. `.env` is gitignored.

## Failure modes

| Failure | Behaviour | How you see it | Action |
|---|---|---|---|
| Empty, oversized, binary or control-char input | `BLOCK`, `INPUT_REJECTED:<code>` | `scan` log `reason_codes` | caller fixes input |
| Body larger than the limit | 413 + `BLOCK`, body not parsed | `request` log status 413 | raise `PII_GATE_MAX_CHARS` if legitimate |
| Detector or engine exception | `BLOCK`, `ENGINE_ERROR` | `engine_error` log with exception type | investigate; the gate stays closed |
| Policy corpus missing or rule cites unknown clause | `/health` 503, all scans 503 + `BLOCK` | `startup_failed` log | fix the policy deploy, roll back |
| Ollama blip (refused, timeout, 429/502/503/504) | retried with backoff, within the deadline; usually `ok` | `llm_retry`, `attempts` > 1 in the response | none if it recovers |
| Ollama down, or retries exhausted | `/v1/assist` gives `degraded` + gate result | `llm_unavailable` with `retryable: true`, `/health` assistant=unavailable | none needed; core unaffected |
| Ollama permanent error (404 model missing, 400, 500, malformed reply) | `degraded` immediately, **not retried** | `llm_unavailable` with `retryable: false` | `ollama pull <model>` or fix config |
| LLM returns junk or PII | `invalid_output` / redacted / `output_withheld`, **not retried** | `llm_invalid_output`, `output_decision` | review prompt or model |
| False positive (over-block) | `BLOCK` or `REDACT` of benign text | user report + request ID | Privacy Office route (DH-7.2); add eval case, fix, release |
| False negative (missed PII) | leak to downstream | eval or red-team, incident | **highest severity**: add eval case, fix detector, release; downstream purge |

## Retry policy (system vs business errors)

| Class | Examples | Retried? | Who decides |
|---|---|---|---|
| Transient system | LLM connect refused or timeout; HTTP 429/502/503/504 | **yes**, up to 3 attempts, jittered backoff, one overall deadline | the gate (`assistant.py`) |
| Permanent system | LLM 4xx/500, malformed reply; gate `ENGINE_ERROR` (500) | no: degrade or fail closed | – |
| Business | `BLOCK`, `INPUT_REJECTED`, 413, 422, `invalid_output`, `output_withheld` | **never**: deterministic, same input gives the same answer | – |
| Gate not ready | 503 `SERVICE_NOT_READY` | caller may retry: `retryable: true`, `Retry-After: 30` | the caller |

Callers read `retryable` in any error body. Rationale: [DR-6](decisions.md#dr-6-retry-transient-system-failures-only-business-outcomes-are-final).

## Rollback and degrade

- **Degrade:** the assistant is optional. Setting `PII_GATE_OLLAMA_URL=""` disables it immediately, and the gate is unaffected.
- **Rollback:** images are immutable, so redeploy the previous image digest. The policy corpus ships in the image, so a policy rollback is the same operation.
- **Never fail open.** There is deliberately no switch that bypasses the gate. If the gate is down, callers must treat the text as blocked.

## Local to cloud

| Concern | Local (this repo) | Cloud (proposed) |
|---|---|---|
| Build and verify | `make verify`, `make docker-smoke` | same targets in CI, plus image scan, SBOM, cosign signing |
| Promote | n/a | PR → CI green → image tagged by git SHA → dev (auto) → staging (eval gate on red-team set) → prod (approval, canary) |
| Runtime | uvicorn or Docker on localhost | managed containers behind an internal API gateway (mTLS, authN, rate limit), 2+ replicas across zones |
| Policy changes | edit `policies/*.md` + `RULES` | same files via PR, evals must pass; version visible in `/health` |
| LLM | Ollama (optional) | approved private model endpoint; credentials from secrets manager |
| Logs and alerts | stderr JSON | central logging/SIEM; alerts on BLOCK-rate spike, `engine_error`, 5xx, p95 latency |
