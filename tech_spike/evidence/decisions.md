# Decision records

## DR-1: Deterministic, checksum-validated detection instead of ML/LLM NER

**Context.** The gate is a control in a regulated environment. It must be explainable, reproducible and fast, and it must run with no model download or API key.

**Decision.** Use regex candidates confirmed by official checksums: Luhn (cards), TFN mod-11, ABN mod-89, Medicare check digit. Context keywords confirm BSB and account numbers. A fallback redacts any unclaimed run of 8+ digits.

**Trade-off.**
- Gains: about 1 ms per request, identical output on every run, and each finding states *why* (`method: checksum | pattern | context | fallback`).
- Costs: names, addresses and dates of birth are **not detected**. This is reported in the evals as an out-of-scope probe (4 of 4 not redacted) and recorded in policy DH-4.3.

**Revisit when** free-text PII matters more than auditability. Add NER as one extra `Detector`, behind the same evals.

## DR-2: Retrieval (RAG) explains and cites policy but never makes the decision

**Context.** We wanted decisions grounded in written policy, and a way to answer "can I do X?" questions.

**Decision.**
- ALLOW/REDACT/BLOCK comes from a fixed **rule table** (`policy.py`). Each rule cites a clause ID, and `check_rules()` confirms that clause exists at startup.
- BM25 retrieval is used only to **explain**: `/v1/explain`, the MCP `explain_policy` tool, and citation text.
- Below a calibrated score (3.0) it **abstains** and refers the user to the Privacy Office.

**Trade-off.** Policy wording and rules can drift apart; the startup check only verifies that clause IDs exist. In return, a retrieval ranking error, which did happen (see agentic-workflow.md, the possessive bug), can never cause a PII leak.

## DR-3: Fail closed everywhere; BLOCK withholds even redacted text; BLOCK is HTTP 200

**Decision.**
- Every failure path ends in `BLOCK`: invalid input, engine exception, unmapped type, missing corpus, oversized body, unhandled error.
- On `BLOCK`, `released_text` is `null`. We don't return a redacted preview, so a careless caller can't use it.
- A policy BLOCK returns **200**, because it is a correct answer. HTTP errors (413, 422, 500, 503) are kept for real faults, and every error body still includes `"decision": "BLOCK"`.

**Trade-off.** More friction for users, since an over-block needs the Privacy Office route in DH-7.2. That's accepted, because a false negative is the costly error here.

## DR-4: The LLM is optional and sits between two gates; it is not exposed via MCP

**Decision.**
- The assistant runs in three steps: gate on the input, then the LLM (redacted text only), then a verifier that validates the schema and re-scans the output with the gate.
- With no Ollama the result is `degraded`; `/health` reports it, but readiness doesn't depend on it.
- The MCP tools stay **read-only and closed-world**, so there's no LLM-backed tool.

**Trade-off.** It isn't verified against a real model (Ollama was intentionally not installed), so JSON compliance of a small model is unproven. The design fails closed (`invalid_output`) rather than leaking. The calling agent already has its own LLM, so offering a second one over MCP would add risk for little value.

## DR-5: Conservative overlap resolution (precision traded for zero leaks)

**Decision.**
- Overlapping candidates merge to their **union span**, so no fragment survives.
- The label comes from the strongest method (checksum > pattern > context > fallback), then the nearest context keyword, then length.
- For example, a 9-digit number after "account" that also passes the TFN checksum is labelled TFN, and so BLOCKed.

**Trade-off.** Some over-blocking and mislabels: a 1-in-11 chance for 9-digit account numbers. Leak rate is the hard gate (0); precision has a ≥ 0.90 target.

## DR-6: Retry transient system failures only; business outcomes are final

**Decision.**
- **Retried:** the one remote call, the LLM, on transient failures only: connection errors, timeouts, and HTTP 429/502/503/504. At most `PII_GATE_LLM_MAX_ATTEMPTS` (default 3) attempts, jittered exponential backoff (0.2 s, 0.4 s, …), `Retry-After` honoured but capped at 5 s, and **one overall deadline** (`PII_GATE_LLM_TIMEOUT`) that covers all attempts. When retries run out, the result degrades to the gate result.
- **Not retried, system:** permanent faults such as other 4xx (e.g. 404 when the model isn't pulled), 500, or a malformed reply. Retrying these only adds latency.
- **Not retried, business:**
  - gate `BLOCK` and input rejection: the gate is deterministic, so the same input gives the same answer;
  - `invalid_output` and `output_withheld`: at temperature 0 the model repeats itself, and re-asking until the output passes would launder an unsafe answer.
- **The API tells callers which is which.** Error bodies carry `retryable`. 503 not-ready is `true`, with `Retry-After: 30`. 413, 422 and 500 are `false`. A 200 `BLOCK` is a decision, not an error.

**Trade-off.** With Ollama down, `/v1/assist` waits for about 0.5 s of backoff before degrading. There's no circuit breaker yet, so each request pays that cost. In production, add a breaker (open after N failures, half-open probe) so a dead dependency fails fast.

## What we intentionally did not build

- Name, address and DOB detection (needs NER); non-English text; attachments, PDFs and images.
- Reversible tokenisation or a vault (re-identification is a separate, higher-risk control).
- AuthN/AuthZ, rate limiting, multi-tenancy. These belong at the API gateway in production.
- Cloud deployment, image signing, SBOM. Described in [operate.md](operate.md), not built.
- An LLM quality eval (summary accuracy). Needs a model; listed as a gap in [verify.md](verify.md).
