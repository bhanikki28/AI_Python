import pytest

from pii_gate.detectors import Finding, detect, resolve_overlaps


def types(text):
    return [f.entity_type for f in detect(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Card 4111 1111 1111 1111 was charged twice", "CARD_NUMBER"),
        ("amex 3782 822463 10005", "CARD_NUMBER"),
        ("My TFN is 123 456 782.", "TFN"),
        ("ABN 51 824 753 556", "ABN"),
        ("Medicare 2123 45670 1", "MEDICARE"),
        ("email jane.citizen@example.com please", "EMAIL"),
        ("mobile 0412 345 678", "PHONE_AU"),
        ("call +61 412 345 678", "PHONE_AU"),
        ("office (02) 9876 5432", "PHONE_AU"),
        ("BSB 062-000", "BSB"),
        ("BSB: 062000", "BSB"),
        ("account number 12345678", "ACCOUNT_NUMBER"),
        ("acc 1234 5678", "ACCOUNT_NUMBER"),
    ],
)
def test_detects_each_entity_type(text, expected):
    assert types(text) == [expected]


@pytest.mark.parametrize(
    "text",
    [
        "Your order on 12/05/2026 for $1,234.56 has shipped.",
        "Reference INV-2026-000123 is closed.",
        "Call us on 1300 650 000 or 1800 123 456.",
        "Postcode 2000, unit 12, 45 George St.",
        "I waited 3 weeks and 2 days.",
    ],
)
def test_no_false_positives_on_benign_numbers(text):
    assert detect(text) == []


def test_invalid_checksum_still_redacted_by_fallback():
    # Typo'd TFN fails the checksum but a 9-digit run is still treated as sensitive.
    assert types("TFN 123 456 789") == ["NUMBER_UNCLASSIFIED"]


def test_card_failing_luhn_still_redacted_by_fallback():
    assert types("card 4111 1111 1111 1112") == ["NUMBER_UNCLASSIFIED"]


def test_multiple_entities_in_order():
    text = "Card 4111 1111 1111 1111, mobile 0412 345 678, email a.b@example.com"
    assert types(text) == ["CARD_NUMBER", "PHONE_AU", "EMAIL"]


def test_digits_in_email_local_part_stay_part_of_email():
    text = "id 123456782@example.com"
    [finding] = detect(text)
    assert finding.entity_type == "EMAIL"
    assert text[finding.start : finding.end] == "123456782@example.com"


def test_overlap_merges_to_union_with_strongest_label():
    candidates = [
        Finding("NUMBER_UNCLASSIFIED", 0, 12, "fallback"),
        Finding("TFN", 4, 15, "checksum"),
        Finding("EMAIL", 20, 30, "pattern"),
    ]
    merged = resolve_overlaps(candidates)
    assert merged == [
        Finding("TFN", 0, 15, "checksum"),
        Finding("EMAIL", 20, 30, "pattern"),
    ]


def test_digits_inside_words_are_ignored():
    assert detect("model ABC123456789X") == []


def test_finding_dict_has_no_raw_value():
    [finding] = detect("TFN 123 456 782")
    assert set(finding.to_dict()) == {"type", "start", "end", "method"}
