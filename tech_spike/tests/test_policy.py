import pytest

from pii_gate.detectors import Finding
from pii_gate.knowledge import PolicyIndex, default_index, parse_clauses
from pii_gate.policy import BULK_THRESHOLD, Decision, check_rules, decide


def f(entity_type, start=0):
    return Finding(entity_type, start, start + 1, "pattern")


def test_no_findings_allows():
    assert decide([]) == (Decision.ALLOW, [])


def test_contact_details_redact_with_citation():
    decision, reasons = decide([f("EMAIL"), f("PHONE_AU", 5)])
    assert decision == Decision.REDACT
    assert {r.clause_id for r in reasons} == {"DH-4.1"}


def test_strictest_rule_wins():
    decision, reasons = decide([f("EMAIL"), f("TFN", 5)])
    assert decision == Decision.BLOCK
    assert reasons[0].entity_type == "TFN"
    assert reasons[0].clause_id == "DH-3.1"


def test_bulk_data_blocks():
    decision, reasons = decide([f("EMAIL", i) for i in range(BULK_THRESHOLD)])
    assert decision == Decision.BLOCK
    assert reasons[0].code == "BULK_DATA"


def test_unmapped_entity_fails_closed():
    decision, reasons = decide([f("PASSPORT")])
    assert decision == Decision.BLOCK
    assert reasons[0].code == "UNMAPPED_ENTITY"


def test_rules_reference_real_clauses():
    check_rules(default_index())


def test_check_rules_detects_missing_clause():
    index = PolicyIndex(parse_clauses("### DH-1.2 Only clause\nbody", "x.md"))
    with pytest.raises(ValueError, match="missing"):
        check_rules(index)
