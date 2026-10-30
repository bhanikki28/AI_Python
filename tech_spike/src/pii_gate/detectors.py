"""Deterministic detectors for Australian banking-style PII.

Each detector proposes candidate spans; a checksum or nearby context keyword
confirms them. Overlapping candidates are merged into one span labelled with the
strongest interpretation, so every flagged character is redacted (no partial
leaks) and ties lean towards the more sensitive type. Raw values are never stored.
"""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from pii_gate import checksums

# Digit-run boundaries: a candidate must not be glued to a word, hyphen or "@",
# and must not be the head/tail of a longer space-separated run of digits.
START = r"(?<![\w-])(?<!\d )"
END = r"(?![\w@-])(?! \d)"

CONTEXT_WINDOW = 40

# Higher wins when candidates overlap.
STRENGTH = {"checksum": 3, "pattern": 2, "context": 1, "fallback": 0}


@dataclass(frozen=True)
class Finding:
    entity_type: str
    start: int
    end: int
    method: str
    context_hit: bool = False

    @property
    def rank(self) -> tuple[int, bool, int]:
        return (STRENGTH[self.method], self.context_hit, self.end - self.start)

    def to_dict(self) -> dict:
        # Deliberately excludes the matched value.
        return {
            "type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "method": self.method,
        }


@dataclass(frozen=True)
class Detector:
    entity_type: str
    pattern: re.Pattern[str]
    method: str
    validate: Callable[[str], bool] | None = None
    context: re.Pattern[str] | None = None
    require_context: bool = False

    def find(self, text: str) -> Iterable[Finding]:
        for m in self.pattern.finditer(text):
            if self.validate and not self.validate(m.group()):
                continue
            window = text[max(0, m.start() - CONTEXT_WINDOW) : m.start()]
            context_hit = bool(self.context and self.context.search(window))
            if self.require_context and not context_hit:
                continue
            yield Finding(self.entity_type, m.start(), m.end(), self.method, context_hit)


def _digit_pattern(body: str) -> re.Pattern[str]:
    return re.compile(START + body + END)


def _keywords(*words: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.IGNORECASE)


def _not_business_number(value: str) -> bool:
    digits = "".join(ch for ch in value if ch.isdigit())
    return not digits.startswith(("1300", "1800"))


DETECTORS: tuple[Detector, ...] = (
    Detector(
        "CARD_NUMBER",
        _digit_pattern(r"\d(?:[ -]?\d){12,18}"),
        "checksum",
        validate=checksums.luhn_valid,
        context=_keywords("card", "visa", "mastercard", "amex", "credit", "debit"),
    ),
    Detector(
        "TFN",
        _digit_pattern(r"\d{3}[ -]?\d{3}[ -]?\d{3}"),
        "checksum",
        validate=checksums.tfn_valid,
        context=_keywords("tfn", "tax file"),
    ),
    Detector(
        "ABN",
        _digit_pattern(r"\d{2} ?\d{3} ?\d{3} ?\d{3}"),
        "checksum",
        validate=checksums.abn_valid,
        context=_keywords("abn"),
    ),
    Detector(
        "MEDICARE",
        _digit_pattern(r"[2-6]\d{3} ?\d{5} ?\d(?: ?\d)?"),
        "checksum",
        validate=checksums.medicare_valid,
        context=_keywords("medicare"),
    ),
    Detector(
        "EMAIL",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
        "pattern",
    ),
    Detector(
        "PHONE_AU",
        _digit_pattern(
            r"(?:(?:\+61 ?4|04)\d{2}[ -]?\d{3}[ -]?\d{3}"
            r"|(?:\+61 ?[2378]|\(0[2378]\)|0[2378])[ -]?\d{4}[ -]?\d{4})"
        ),
        "pattern",
    ),
    Detector(
        "BSB",
        _digit_pattern(r"\d{3}-\d{3}"),
        "pattern",
        context=_keywords("bsb"),
    ),
    Detector(
        "BSB",
        _digit_pattern(r"\d{3} ?\d{3}"),
        "context",
        context=_keywords("bsb"),
        require_context=True,
    ),
    Detector(
        "ACCOUNT_NUMBER",
        _digit_pattern(r"\d(?:[ -]?\d){5,9}"),
        "context",
        context=_keywords("account", "acct", "acc", "a/c"),
        require_context=True,
    ),
    # Safety net: any long digit run nothing else claimed is still redacted.
    Detector(
        "NUMBER_UNCLASSIFIED",
        _digit_pattern(r"\d(?:[ -]?\d){7,}"),
        "fallback",
        validate=_not_business_number,
    ),
)


def resolve_overlaps(candidates: Iterable[Finding]) -> list[Finding]:
    """Merge overlapping candidates into their union, labelled by the top-ranked one."""
    resolved: list[Finding] = []
    group: list[Finding] = []
    group_end = -1
    for f in sorted(candidates, key=lambda f: f.start):
        if group and f.start >= group_end:
            resolved.append(_merge(group))
            group = []
        group.append(f)
        group_end = max(group_end, f.end) if len(group) > 1 else f.end
    if group:
        resolved.append(_merge(group))
    return resolved


def _merge(group: list[Finding]) -> Finding:
    best = max(group, key=lambda f: f.rank)
    return replace(best, start=min(f.start for f in group), end=max(f.end for f in group))


def detect(text: str, detectors: Iterable[Detector] = DETECTORS) -> list[Finding]:
    return resolve_overlaps(f for d in detectors for f in d.find(text))
