"""Checksum validators for Australian identifiers and payment cards.

Checksums turn a "looks like a number" match into a high-confidence finding,
which is what keeps precision up without an ML model.
"""


def _digits(value: str) -> list[int]:
    return [int(ch) for ch in value if ch.isdigit()]


def _degenerate(digits: list[int]) -> bool:
    # All-same digits (e.g. 0000 0000 ...) satisfy several checksums trivially.
    return len(set(digits)) <= 1


def luhn_valid(value: str) -> bool:
    """Payment card numbers (13-19 digits)."""
    digits = _digits(value)
    if not 13 <= len(digits) <= 19 or _degenerate(digits):
        return False
    total = 0
    for i, n in enumerate(reversed(digits)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


TFN_WEIGHTS = (1, 4, 3, 7, 5, 8, 6, 9, 10)


def tfn_valid(value: str) -> bool:
    """9-digit Tax File Number: weighted sum divisible by 11."""
    digits = _digits(value)
    if len(digits) != 9 or _degenerate(digits):
        return False
    return sum(w * d for w, d in zip(TFN_WEIGHTS, digits, strict=True)) % 11 == 0


ABN_WEIGHTS = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)


def abn_valid(value: str) -> bool:
    """11-digit ABN: subtract 1 from the first digit, weighted sum divisible by 89."""
    digits = _digits(value)
    if len(digits) != 11 or _degenerate(digits):
        return False
    digits[0] -= 1
    return sum(w * d for w, d in zip(ABN_WEIGHTS, digits, strict=True)) % 89 == 0


MEDICARE_WEIGHTS = (1, 3, 7, 9, 1, 3, 7, 9)


def medicare_valid(value: str) -> bool:
    """10-digit Medicare number (optional 11th IRN digit); first digit 2-6, 9th is check digit."""
    digits = _digits(value)
    if len(digits) not in (10, 11) or not 2 <= digits[0] <= 6:
        return False
    check = sum(w * d for w, d in zip(MEDICARE_WEIGHTS, digits[:8], strict=True)) % 10
    return check == digits[8]
