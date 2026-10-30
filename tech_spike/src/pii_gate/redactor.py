"""Replace detected spans with typed placeholders such as [CARD_NUMBER]."""

from collections.abc import Iterable

from pii_gate.detectors import Finding


def redact(text: str, findings: Iterable[Finding]) -> str:
    """Findings must be non-overlapping, as returned by detectors.detect()."""
    parts: list[str] = []
    cursor = 0
    for f in sorted(findings, key=lambda f: f.start):
        parts.append(text[cursor : f.start])
        parts.append(f"[{f.entity_type}]")
        cursor = f.end
    parts.append(text[cursor:])
    return "".join(parts)
