# Verification

**One command:** `make verify` runs lint (ruff), then tests (pytest), then evals. It exits non-zero on any failure, and CI runs the same command.

## Results at submission

| Check | Result |
|---|---|
| Lint (`ruff check src tests evals examples`) | clean |
| Unit and integration tests | **129 passed** (local Python 3.14; CI Python 3.11 and 3.13) |
| Evals | all 6 gated metrics pass (below) |
| Dependency audit (`make audit`, pip-audit) | no known vulnerabilities |
| Container smoke (`make docker-smoke`) | PASS: health, ALLOW/REDACT/BLOCK, UI, PII-free container logs, non-root uid 10001 |
| GitHub Actions run `41138931135` (commit `6860a0f`) | all 4 jobs green; logs show `129 passed`, `EVALS PASSED`, `SMOKE PASS` |

## Evals (`make eval`, report in `reports/eval-report.md`)

| Metric | Value | Target |
|---|---|---|
| Detection precision (typed span overlap) | 1.000 | ≥ 0.90 |
| Detection recall | 1.000 | ≥ 0.95 |
| **Leak rate** (any character of a labelled entity left unredacted) | **0.000** (0 of 105) | = 0 (hard gate) |
| Decision accuracy (67 cases) | 1.000 | ≥ 0.95 |
| RAG hit@3 (18 answerable questions) | 1.000 | ≥ 0.90 |
| RAG abstain accuracy (24 questions, 6 should abstain) | 1.000 | ≥ 0.90 |
| RAG top-1 accuracy | 0.889 | reported only |
| Out-of-scope probes (names, address, DOB) | 4 of 4 not redacted | reported only (known gap) |

**Dataset:** 69 cases, generated from a fixed seed by `evals/generate_dataset.py`. CI regenerates it and fails if it differs.
- 42 positive, 3 bulk, 14 hard negatives (dates, amounts, references, 1300 numbers), 6 evasion (zero-width, full-width, case, no spaces), 2 invalid inputs, 2 probes.
- Expected decisions come from an **independent oracle** restating the policy, not from the engine under test.

**How to read these numbers.** The 1.000 scores mean the gate works as designed on synthetic data built from the formats it targets, and that regressions are caught. They are **not** a claim about accuracy on real customer text.

**Evals earned their place.** On the first run all thresholds passed (precision 0.953, recall 0.971), but the failure list exposed two real bugs: BSB vs account mislabelling, and hyphenated dates flagged as numbers. Both were fixed with regression tests. Read the failures, not just the pass/fail line.

## Test inventory (129)

| Area | Tests | Highlights |
|---|---|---|
| Checksums, detectors, redaction, validation | 50 | false-positive guards, evasion, union-merge, no raw value in findings |
| Policy, gate, knowledge (RAG) | 24 | strictest wins, bulk, unmapped type fails closed, engine error fails closed, abstain, possessive regression |
| API, CLI, config | 25 | 422/413/503 paths, **no input echo**, request ID propagation, **log content has no PII**, bad config fails fast |
| MCP server | 7 | tool annotations, instructions, no PII in tool output, **real stdio subprocess** |
| Assistant (fake Ollama) | 18 | LLM sees redacted text only, blocked input never sent, verifier redacts or withholds LLM PII, invalid output fails closed, refused/timeout/5xx degrade |
| Eval metrics, smoke | 5 | span location, partial-leak detection |

## Where each check runs

| Check | Local (dev) | PR / push CI | Release pipeline (proposed) |
|---|---|---|---|
| Lint, tests, evals (`make verify`) | ✅ | ✅ py3.11 + py3.13 | ✅ |
| Dataset reproducibility | `make dataset` + `git diff` | ✅ | ✅ |
| Dependency audit | `make audit` | ✅ | ✅ + licence check |
| Container build + smoke | `make docker-smoke` | ✅ | ✅ |
| Image scan (Trivy), SBOM, signing (cosign) | – | – | proposed |
| Eval on a refreshed or red-team dataset | – | – | proposed, gating promotion |
| Live LLM eval (JSON compliance, summary quality) | with Ollama | – | proposed, against an approved model |

## Known gaps

- **Synthetic data only.** No real-world precision/recall estimate. Next step: a red-team set written by people, not by the generator.
- **No names, addresses or DOB** (see DR-1).
- **Assistant not run against a real LLM.** All 18 assistant tests use a fake Ollama.
- **UI not browser-tested.** Only "served and renders the title" is automated. The UI was checked by hand.
- **No load or performance test.** Per-request latency is about 1 ms in logs, but there's no p95 under concurrency.
- **GitHub Actions pinned to major tags** (`@v4`), not commit SHAs. In production, pin to SHAs.
- **Claude Code MCP registration** is documented but wasn't exercised from the `claude` CLI here (not on PATH). The MCP server is tested with the SDK client over real stdio.
