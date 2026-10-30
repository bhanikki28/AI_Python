import pytest

from evals.metrics import TypedCounts, leaked, locate, match_entities


def test_locate_handles_repeated_values():
    assert locate("a 12 b 12", ["12", "12"]) == [(2, 4), (7, 9)]


def test_locate_raises_when_value_missing():
    with pytest.raises(ValueError):
        locate("abc", ["zzz"])


def test_leak_detects_partial_coverage():
    assert not leaked((5, 10), [(0, 12)])
    assert leaked((5, 10), [(5, 8)])  # last two characters survive
    assert leaked((5, 10), [])


def test_match_entities_counts_tp_fp_fn():
    counts = TypedCounts()
    expected = [("EMAIL", (0, 10)), ("TFN", (20, 31))]
    predicted = [("EMAIL", (0, 10)), ("NUMBER_UNCLASSIFIED", (20, 31)), ("PHONE_AU", (40, 50))]
    match_entities(expected, predicted, counts)
    assert counts.get("EMAIL").tp == 1
    assert counts.get("TFN").fn == 1
    assert counts.get("NUMBER_UNCLASSIFIED").fp == 1
    assert counts.get("PHONE_AU").fp == 1
    micro = counts.micro
    assert (micro.tp, micro.fp, micro.fn) == (1, 2, 1)
