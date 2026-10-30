from pii_gate.detectors import detect
from pii_gate.redactor import redact
from pii_gate.validation import validate_input

RAW_VALUES = ["4111 1111 1111 1111", "0412 345 678", "jane.doe@example.com", "123 456 782"]


def test_redacts_with_typed_placeholders():
    text = (
        "Hi, my card 4111 1111 1111 1111 was charged twice. Call me on 0412 345 678 "
        "or email jane.doe@example.com. My TFN is 123 456 782."
    )
    out = redact(text, detect(text))
    assert out == (
        "Hi, my card [CARD_NUMBER] was charged twice. Call me on [PHONE_AU] "
        "or email [EMAIL]. My TFN is [TFN]."
    )
    for raw in RAW_VALUES:
        assert raw not in out


def test_clean_text_unchanged():
    text = "The branch was closed on Tuesday."
    assert redact(text, detect(text)) == text


def test_evasion_with_zero_width_and_fullwidth_digits():
    sneaky = "card 4111​1111​1111​1111 and tfn １２３ ４５６ ７８２"
    clean = validate_input(sneaky)
    out = redact(clean, detect(clean))
    assert out == "card [CARD_NUMBER] and tfn [TFN]"
