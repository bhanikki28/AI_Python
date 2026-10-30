import pytest

from pii_gate import checksums

# All values are published test numbers or synthetic values built to pass checksums.


@pytest.mark.parametrize(
    "value",
    ["4111 1111 1111 1111", "5555-5555-5555-4444", "378282246310005"],
)
def test_luhn_accepts_scheme_test_cards(value):
    assert checksums.luhn_valid(value)


@pytest.mark.parametrize(
    "value",
    ["4111 1111 1111 1112", "0000 0000 0000 0000", "4111 1111 111"],
)
def test_luhn_rejects_invalid(value):
    assert not checksums.luhn_valid(value)


def test_tfn():
    assert checksums.tfn_valid("123 456 782")
    assert not checksums.tfn_valid("123 456 789")
    assert not checksums.tfn_valid("000 000 000")


def test_abn():
    assert checksums.abn_valid("51 824 753 556")
    assert not checksums.abn_valid("51 824 753 557")


def test_medicare():
    assert checksums.medicare_valid("2123 45670 1")
    assert not checksums.medicare_valid("2123 45679 1")
    assert not checksums.medicare_valid("7123 45670 1")  # first digit must be 2-6
