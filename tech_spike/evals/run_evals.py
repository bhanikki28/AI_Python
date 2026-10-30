"""Run the PII Gate eval suite and fail (exit 1) if any threshold is missed.

Usage: python -m evals.run_evals
Writes reports/eval-report.md and reports/eval-results.json. Output lists case IDs
and entity types only, never entity values.
"""

import json
import sys
from pathlib import Path

from evals.metrics import TypedCounts, leaked, locate, match_entities
from pii_gate import detectors, gate
from pii_gate.knowledge import explain
from pii_gate.validation import InputRejected, validate_input

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "sample-data" / "eval_cases.jsonl"
QUESTIONS = ROOT / "sample-data" / "policy_questions.jsonl"
REPORTS = ROOT / "reports"

# Mirrors the success criteria in evidence/intent.md.
THRESHOLDS = {
    "detection_precision": (">=", 0.90),
    "detection_recall": (">=", 0.95),
    "leak_rate": ("<=", 0.0),
    "decision_accuracy": (">=", 0.95),
    "rag_hit_at_3": (">=", 0.90),
    "rag_abstain_accuracy": (">=", 0.90),
}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def eval_gate(cases: list[dict]) -> tuple[dict, dict]:
    counts = TypedCounts()
    entities = leaks = correct = gated = 0
    failures: list[str] = []
    probe = {"entities": 0, "leaked": 0}

    for case in cases:
        result = gate.scan(case["text"])
        if case["probe"]:
            clean = validate_input(case["text"])
            spans = [(f.start, f.end) for f in detectors.detect(clean)]
            for span in locate(clean, [e["value"] for e in case["entities"]]):
                probe["entities"] += 1
                probe["leaked"] += leaked(span, spans)
            continue

        gated += 1
        if result.decision.name == case["expected_decision"]:
            correct += 1
        else:
            failures.append(
                f"{case['id']}: decision {result.decision.name}, "
                f"expected {case['expected_decision']}"
            )

        try:
            clean = validate_input(case["text"])
        except InputRejected:
            continue
        findings = detectors.detect(clean)
        expected_spans = locate(clean, [e["value"] for e in case["entities"]])
        expected = [(e["type"], s) for e, s in zip(case["entities"], expected_spans, strict=True)]
        predicted = [(f.entity_type, (f.start, f.end)) for f in findings]
        before = counts.micro
        match_entities(expected, predicted, counts)
        after = counts.micro
        if after.fp > before.fp or after.fn > before.fn:
            got = sorted(t for t, _ in predicted)
            want = sorted(t for t, _ in expected)
            failures.append(f"{case['id']}: detected {got}, expected {want}")

        redacted_spans = [(f.start, f.end) for f in findings]
        for etype, span in expected:
            entities += 1
            if leaked(span, redacted_spans):
                leaks += 1
                failures.append(f"{case['id']}: LEAK of {etype}")

    micro = counts.micro
    metrics = {
        "detection_precision": micro.precision,
        "detection_recall": micro.recall,
        "leak_rate": leaks / entities if entities else 0.0,
        "decision_accuracy": correct / gated if gated else 1.0,
    }
    detail = {
        "cases": gated,
        "entities": entities,
        "leaks": leaks,
        "per_type": {
            t: {"tp": c.tp, "fp": c.fp, "fn": c.fn,
                "precision": c.precision, "recall": c.recall}
            for t, c in sorted(counts.by_type.items())
        },
        "probes": probe,
        "failures": failures,
    }
    return metrics, detail


def eval_rag(questions: list[dict]) -> tuple[dict, dict]:
    answerable = [q for q in questions if q["expected"]]
    unanswerable = [q for q in questions if not q["expected"]]
    hits = top1 = abstain_ok = 0
    failures = []

    for q in answerable:
        result = explain(q["question"])
        ids = [h.clause.id for h in result.hits]
        if result.answered and set(ids) & set(q["expected"]):
            hits += 1
            top1 += ids[0] in q["expected"]
            abstain_ok += 1
        else:
            failures.append(f"{q['id']}: got {ids or 'ABSTAIN'}, expected one of {q['expected']}")
            abstain_ok += result.answered
    for q in unanswerable:
        result = explain(q["question"])
        if result.answered:
            failures.append(f"{q['id']}: answered {result.hits[0].clause.id}, expected ABSTAIN")
        else:
            abstain_ok += 1

    metrics = {
        "rag_hit_at_3": hits / len(answerable) if answerable else 1.0,
        "rag_abstain_accuracy": abstain_ok / len(questions) if questions else 1.0,
    }
    detail = {
        "questions": len(questions),
        "top1_accuracy": top1 / len(answerable) if answerable else 1.0,
        "failures": failures,
    }
    return metrics, detail


def check(metrics: dict) -> dict[str, bool]:
    results = {}
    for name, (op, target) in THRESHOLDS.items():
        value = metrics[name]
        results[name] = value >= target if op == ">=" else value <= target
    return results


def render(metrics: dict, passed: dict, gate_detail: dict, rag_detail: dict) -> str:
    lines = [
        "# PII Gate eval report",
        "",
        "| Metric | Value | Target | Result |",
        "|---|---|---|---|",
    ]
    for name, (op, target) in THRESHOLDS.items():
        status = "PASS" if passed[name] else "FAIL"
        lines.append(f"| {name} | {metrics[name]:.3f} | {op} {target} | {status} |")

    lines += [
        "",
        f"Gate cases: {gate_detail['cases']}, labelled entities: {gate_detail['entities']}, "
        f"leaks: {gate_detail['leaks']}. "
        f"Policy questions: {rag_detail['questions']}, "
        f"RAG top-1 accuracy: {rag_detail['top1_accuracy']:.3f} (reported, not gated).",
        "",
        "## Per entity type",
        "",
        "| Type | TP | FP | FN | Precision | Recall |",
        "|---|---|---|---|---|---|",
    ]
    for t, c in gate_detail["per_type"].items():
        lines.append(
            f"| {t} | {c['tp']} | {c['fp']} | {c['fn']} "
            f"| {c['precision']:.3f} | {c['recall']:.3f} |"
        )

    probes = gate_detail["probes"]
    lines += [
        "",
        "## Out-of-scope probes (not gated)",
        "",
        f"Names, addresses and dates of birth (policy DH-4.3, known gap): "
        f"{probes['leaked']}/{probes['entities']} probe entities not redacted.",
        "",
        "## Failures",
        "",
    ]
    failures = gate_detail["failures"] + rag_detail["failures"]
    lines += [f"- {f}" for f in failures] or ["None."]
    return "\n".join(lines) + "\n"


def main() -> int:
    gate_metrics, gate_detail = eval_gate(load(CASES))
    rag_metrics, rag_detail = eval_rag(load(QUESTIONS))
    metrics = gate_metrics | rag_metrics
    passed = check(metrics)

    report = render(metrics, passed, gate_detail, rag_detail)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "eval-report.md").write_text(report, "utf-8")
    (REPORTS / "eval-results.json").write_text(
        json.dumps({"metrics": metrics, "passed": passed, "gate": gate_detail, "rag": rag_detail},
                   indent=2),
        "utf-8",
    )
    print(report)
    if not all(passed.values()):
        print("EVALS FAILED: " + ", ".join(k for k, ok in passed.items() if not ok))
        return 1
    print("EVALS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
