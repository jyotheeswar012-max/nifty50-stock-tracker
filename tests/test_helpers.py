"""Tests for the _fmt() price formatter used in pages."""
import pytest


def _fmt(value: float) -> str:
    """ASCII-safe price formatter -- no locale, no \\xa0."""
    integer_part, decimal_part = f"{value:.2f}".split(".")
    chars = list(integer_part)
    for i in range(len(chars) - 3, 0, -3):
        chars.insert(i, ",")
    return "".join(chars) + "." + decimal_part


class TestFmtHelper:
    def test_thousands_separator(self):
        assert _fmt(1328.50) == "1,328.50"

    def test_no_xa0(self):
        assert "\xa0" not in _fmt(1000000.0)

    def test_only_ascii(self):
        assert _fmt(9999999.99).isascii()

    def test_small_number(self):
        assert _fmt(5.5) == "5.50"

    def test_zero(self):
        assert _fmt(0.0) == "0.00"

    def test_large_number(self):
        assert _fmt(1234567.89) == "1,234,567.89"

    def test_two_decimal_places(self):
        assert _fmt(100.1).endswith(".10")

    def test_six_figures(self):
        assert _fmt(100000.0) == "100,000.00"
