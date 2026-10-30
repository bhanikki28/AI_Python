"""The gate pipeline: validate -> detect -> decide -> redact -> cite policy.

Every failure path ends in BLOCK. Redacted text is only released for ALLOW/REDACT.
"""

from dataclasses import dataclass, field

from pii_gate import detectors
from pii_gate.knowledge import PolicyIndex, default_index
from pii_gate.logging_setup import get_logger
from pii_gate.policy import FAIL_CLOSED_CLAUSE, Decision, Reason, decide
from pii_gate.redactor import redact
from pii_gate.validation import DEFAULT_MAX_CHARS, InputRejected, validate_input

log = get_logger("gate")


@dataclass
class GateResult:
    decision: Decision
    released_text: str | None
    findings: list[detectors.Finding] = field(default_factory=list)
    reasons: list[Reason] = field(default_factory=list)

    def to_dict(self, index: PolicyIndex | None = None) -> dict:
        index = index or default_index()
        return {
            "decision": self.decision.name,
            "released_text": self.released_text,
            "findings": [f.to_dict() for f in self.findings],
            "reasons": [_reason_dict(r, index) for r in self.reasons],
        }


def _reason_dict(reason: Reason, index: PolicyIndex) -> dict:
    clause = index.get(reason.clause_id)
    return {
        "code": reason.code,
        "decision": reason.decision.name,
        "entity_type": reason.entity_type,
        "count": reason.count,
        "policy": {
            "id": reason.clause_id,
            "title": clause.title if clause else None,
            "text": clause.body if clause else None,
        },
    }


def scan(text: object, max_chars: int = DEFAULT_MAX_CHARS) -> GateResult:
    try:
        clean = validate_input(text, max_chars)
    except InputRejected as exc:
        return GateResult(
            Decision.BLOCK,
            None,
            reasons=[Reason(f"INPUT_REJECTED:{exc.code}", Decision.BLOCK, FAIL_CLOSED_CLAUSE)],
        )

    try:
        findings = detectors.detect(clean)
        decision, reasons = decide(findings)
        released = redact(clean, findings) if decision != Decision.BLOCK else None
    except Exception as exc:
        # Never fall open: an engine fault must not release uninspected text.
        # Log the exception type only; messages could contain input fragments.
        log.error("engine_error", extra={"fields": {"error_type": type(exc).__name__}})
        return GateResult(
            Decision.BLOCK,
            None,
            reasons=[Reason("ENGINE_ERROR", Decision.BLOCK, FAIL_CLOSED_CLAUSE)],
        )

    return GateResult(decision, released, findings, reasons)
