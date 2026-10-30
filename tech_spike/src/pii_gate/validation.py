"""Input validation. Anything the gate cannot safely inspect is rejected (fail closed)."""

import unicodedata

DEFAULT_MAX_CHARS = 10_000


class InputRejected(ValueError):
    """Raised for input the gate refuses to process. Messages never echo the input."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_input(text: object, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Return normalised text, or raise InputRejected.

    Normalisation (NFKC + dropping invisible format characters) defeats simple
    evasion such as full-width digits or zero-width spaces inside a card number.
    """
    if not isinstance(text, str):
        raise InputRejected("NOT_TEXT", "Input must be a string.")
    if len(text) > max_chars:
        raise InputRejected("TOO_LARGE", f"Input exceeds {max_chars} characters.")

    normalised = unicodedata.normalize("NFKC", text)
    normalised = "".join(ch for ch in normalised if unicodedata.category(ch) != "Cf")

    if any(unicodedata.category(ch) == "Cc" and ch not in "\t\n\r" for ch in normalised):
        raise InputRejected("CONTROL_CHARS", "Input contains control characters.")
    if not normalised.strip():
        raise InputRejected("EMPTY", "Input is empty.")
    if len(normalised) > max_chars:
        raise InputRejected("TOO_LARGE", f"Input exceeds {max_chars} characters.")
    return normalised
