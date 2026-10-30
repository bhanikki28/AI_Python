# Intent

## Problem
Teams in a regulated bank want to use LLMs and analytics on free text such as
complaints, chat transcripts and case notes. That text routinely contains
customer PII: card numbers, account/BSB numbers, TFNs, Medicare numbers,
emails, phone numbers. Sending it unfiltered to a model, a log or a third-party
service is a privacy and regulatory breach (Privacy Act / APPs, PCI DSS, CPS 234).

## Solution (thin slice)
A **pre-processing gate** that every outbound text passes through. It:
1. validates the input (type, size, encoding) and fails closed when it can't;
2. detects sensitive entities with deterministic, checksum-validated detectors;
3. redacts them with typed placeholders (`[CARD_NUMBER]`, `[EMAIL]`, …);
4. returns a policy decision (`ALLOW` / `REDACT` / `BLOCK`) with reason codes,
   **without ever echoing raw PII into logs or responses**;
5. cites the policy clause behind each decision, retrieved from a local
   synthetic policy corpus (**RAG**, BM25/TF-IDF, no model download).

The gate is reachable over REST, CLI, a web UI and an **MCP server** (tool calling
from AI clients). An **optional** LLM assistant (local Ollama) is called only
with redacted text, and a Verifier re-scans its output. When Ollama isn't present,
the system **degrades** to deterministic-only mode. The core path never needs an LLM.

## Intended users
- Platform/AI engineers who put it in front of LLM calls (API).
- Analysts and testers checking text by hand (CLI / web UI).
- Risk and assurance staff who read the eval report as control evidence.

## Assumptions
- Text is English, ≤ 10,000 characters per request (configurable).
- Australian identifier formats are the priority.
- Deterministic detection is preferred over ML for auditability in this slice.

## Constraints
- 3-hour build timebox; runs locally; no paid APIs, credentials or network calls.
- Synthetic data only. All identifiers in the repo are fabricated or are
  published test numbers (e.g. card-scheme test PANs).

## Out of scope
- Free-text names and addresses (needs NER; listed as a next step).
- Non-English text, images, PDFs or attachments.
- Reversible tokenisation and vaulting.
- AuthN/AuthZ, multi-tenancy, and cloud deployment (described, not built).

## Success criteria
| Criterion | Target |
|---|---|
| End-to-end workflow: text → decision + redacted text via API, CLI and UI | Works locally |
| Eval recall on the labelled synthetic set (per entity type) | ≥ 0.95 |
| Eval precision on the labelled synthetic set | ≥ 0.90 |
| **Leak rate** (raw PII surviving in the redacted output) | **0** — hard gate |
| Decision accuracy (ALLOW/REDACT/BLOCK) on the labelled set | ≥ 0.95 |
| RAG retrieval hit@3 (correct policy clause cited) | ≥ 0.90 |
| Ollama absent → assistant reports degraded and the gate still works | Tested |
| Fail-closed: oversized, empty or malformed input → `BLOCK`/4xx, never pass-through | Tested |
| `make verify` runs lint, tests and evals with a non-zero exit on failure | Works |
