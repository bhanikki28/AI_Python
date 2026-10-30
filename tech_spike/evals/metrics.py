"""Metric helpers for the eval harness (pure functions; see tests/test_eval_metrics.py)."""

from dataclasses import dataclass, field

Span = tuple[int, int]


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0


@dataclass
class TypedCounts:
    by_type: dict[str, Counts] = field(default_factory=dict)

    def get(self, entity_type: str) -> Counts:
        return self.by_type.setdefault(entity_type, Counts())

    @property
    def micro(self) -> Counts:
        total = Counts()
        for c in self.by_type.values():
            total.tp += c.tp
            total.fp += c.fp
            total.fn += c.fn
        return total


def locate(text: str, values: list[str]) -> list[Span]:
    """Find each expected value in order, so repeated values map to distinct spans."""
    spans, cursor = [], 0
    for value in values:
        start = text.find(value, cursor)
        if start < 0:
            start = text.find(value)
        if start < 0:
            raise ValueError("expected entity value not found in normalised text")
        spans.append((start, start + len(value)))
        cursor = start + len(value)
    return spans


def overlaps(a: Span, b: Span) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def match_entities(
    expected: list[tuple[str, Span]], predicted: list[tuple[str, Span]], counts: TypedCounts
) -> None:
    """Typed overlap matching: a prediction is a TP if it overlaps an unmatched expected
    entity of the same type."""
    used: set[int] = set()
    for etype, span in expected:
        hit = next(
            (i for i, (ptype, pspan) in enumerate(predicted)
             if i not in used and ptype == etype and overlaps(span, pspan)),
            None,
        )
        if hit is None:
            counts.get(etype).fn += 1
        else:
            used.add(hit)
            counts.get(etype).tp += 1
    for i, (ptype, _) in enumerate(predicted):
        if i not in used:
            counts.get(ptype).fp += 1


def leaked(expected_span: Span, redacted_spans: list[Span]) -> bool:
    """True if any character of the expected entity is not covered by a redacted span."""
    covered = set()
    for start, end in redacted_spans:
        covered.update(range(start, end))
    return any(i not in covered for i in range(*expected_span))
