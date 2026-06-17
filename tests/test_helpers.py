"""Tests for helper/utility functions used across the app."""
import math
import pytest
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# _fmt helper (copied inline so this test is self-contained)
# ---------------------------------------------------------------------------
def _fmt(value: float) -> str:
    """ASCII-safe price formatter -- no locale, no \\xa0."""
    integer_part, decimal_part = f"{value:.2f}".split(".")
    chars = list(integer_part)
    for i in range(len(chars) - 3, 0, -3):
        chars.insert(i, ",")
    return "".join(chars) + "." + decimal_part


# ---------------------------------------------------------------------------
# safe_float helper (mirrors sf() used in multiple pages)
# ---------------------------------------------------------------------------
def safe_float(v, default=0.0):
    try:
        f = float(v)
        return default if (pd.isna(f) or math.isinf(f)) else f
    except Exception:
        return default


class TestFmtHelper:
    def test_thousands_separator(self):
        assert _fmt(1328.50) == "1,328.50"

    def test_no_xa0(self):
        result = _fmt(1000000.0)
        assert "\xa0" not in result

    def test_only_ascii(self):
        result = _fmt(9999999.99)
        assert result.isascii()

    def test_small_number(self):
        assert _fmt(5.5) == "5.50"

    def test_zero(self):
        assert _fmt(0.0) == "0.00"

    def test_large_number(self):
        assert _fmt(1234567.89) == "1,234,567.89"

    def test_two_decimal_places(self):
        result = _fmt(100.1)
        assert result.endswith(".10")


class TestSafeFloat:
    def test_normal_value(self):
        assert safe_float(42.5) == pytest.approx(42.5)

    def test_string_number(self):
        assert safe_float("3.14") == pytest.approx(3.14)

    def test_nan_returns_default(self):
        assert safe_float(float("nan")) == 0.0

    def test_inf_returns_default(self):
        assert safe_float(float("inf")) == 0.0

    def test_none_returns_default(self):
        assert safe_float(None) == 0.0

    def test_invalid_string_returns_default(self):
        assert safe_float("N/A") == 0.0

    def test_custom_default(self):
        assert safe_float(None, default=-1.0) == -1.0
