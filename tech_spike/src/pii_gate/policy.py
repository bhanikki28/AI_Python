"""Deterministic decision rules: entity types -> ALLOW / REDACT / BLOCK with a policy citation.

The rule table is the auditable source of truth. Each rule cites a clause ID that
must exist in the policy corpus; check_rules() is run at startup and in tests.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum

from pii_gate.detectors import Finding
from pii_gate.knowledge import PolicyIndex


class Decision(IntEnum):
    # Ordered by severity so max() picks the strictest outcome.
    ALLOW = 0
    REDACT = 1
    BLOCK = 2


RULES: dict[str, tuple[Decision, str]] = {
    "CARD_NUMBER": (Decision.REDACT, "DH-2.1"),
    "ACCOUNT_NUMBER": (Decision.REDACT, "DH-2.2"),
    "BSB": (Decision.REDACT, "DH-2.2"),
    "TFN": (Decision.BLOCK, "DH-3.1"),
    "MEDICARE": (Decision.BLOCK, "DH-3.2"),
    "ABN": (Decision.REDACT, "DH-3.3"),
    "EMAIL": (Decision.REDACT, "DH-4.1"),
    "PHONE_AU": (Decision.REDACT, "DH-4.1"),
    "NUMBER_UNCLASSIFIED": (Decision.REDACT, "DH-4.2"),
}
FAIL_CLOSED_CLAUSE = "DH-1.2"
BULK_CLAUSE = "DH-6.1"
BULK_THRESHOLD = 8


@dataclass(frozen=True)
class Reason:
    code: str
    decision: Decision
    clause_id: str
    entity_type: str | None = None
    count: int = 0


def check_rules(index: PolicyIndex) -> None:
    cited = {clause for _, clause in RULES.values()} | {FAIL_CLOSED_CLAUSE, BULK_CLAUSE}
    missing = sorted(c for c in cited if index.get(c) is None)
    if missing:
        raise ValueError(f"Rules cite clauses missing from the policy corpus: {missing}")


def decide(findings: Iterable[Finding]) -> tuple[Decision, list[Reason]]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.entity_type] = counts.get(f.entity_type, 0) + 1

    reasons = []
    for entity_type, count in counts.items():
        if entity_type in RULES:
            decision, clause = RULES[entity_type]
            reasons.append(Reason("ENTITY_DETECTED", decision, clause, entity_type, count))
        else:
            # A detector without a rule is config drift: fail closed rather than guess.
            reasons.append(
                Reason("UNMAPPED_ENTITY", Decision.BLOCK, FAIL_CLOSED_CLAUSE, entity_type, count)
            )

    total = sum(counts.values())
    if total >= BULK_THRESHOLD:
        reasons.append(Reason("BULK_DATA", Decision.BLOCK, BULK_CLAUSE, count=total))

    decision = max((r.decision for r in reasons), default=Decision.ALLOW)
    reasons.sort(key=lambda r: (-r.decision, r.clause_id))
    return decision, reasons
