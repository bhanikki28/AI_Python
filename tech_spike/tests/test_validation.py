import pytest

from pii_gate.validation import InputRejected, validate_input


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (None, "NOT_TEXT"),
        (b"bytes", "NOT_TEXT"),
        ("", "EMPTY"),
        ("   \n\t", "EMPTY"),
        ("​​", "EMPTY"),
        ("hi\x00there", "CONTROL_CHARS"),
        ("x" * 11, "TOO_LARGE"),
    ],
)
def test_rejects_unsafe_input(value, code):
    with pytest.raises(InputRejected) as exc:
        validate_input(value, max_chars=10)
    assert exc.value.code == code


def test_rejection_message_does_not_echo_input():
    secret = "4111 1111 1111 1111" * 10
    with pytest.raises(InputRejected) as exc:
        validate_input(secret, max_chars=20)
    assert "4111" not in exc.value.message


def test_accepts_and_normalises():
    assert validate_input("ＡＢＣ​ 123\n") == "ABC 123\n"
