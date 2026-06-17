"""Tests for utils/calculations.py."""
import pytest
import pandas as pd
import numpy as np
from utils.calculations import safe_float, calc_pl, calc_beta_impact, safe_sort


# ---------------------------------------------------------------------------
# safe_float
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# calc_pl
# ---------------------------------------------------------------------------

class TestCalcPl:
    def test_profit(self):
        pl, inv, ret = calc_pl(100, 120, 10)
        assert pl  == pytest.approx(200.0)
        assert inv == pytest.approx(1000.0)
        assert ret == pytest.approx(20.0)

    def test_loss(self):
        pl, inv, ret = calc_pl(200, 150, 5)
        assert pl  == pytest.approx(-250.0)
        assert ret == pytest.approx(-25.0)

    def test_breakeven(self):
        pl, inv, ret = calc_pl(100, 100, 10)
        assert pl  == pytest.approx(0.0)
        assert ret == pytest.approx(0.0)

    def test_zero_qty(self):
        pl, inv, ret = calc_pl(100, 200, 0)
        assert pl  == pytest.approx(0.0)
        assert inv == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calc_beta_impact
# ---------------------------------------------------------------------------

class TestCalcBetaImpact:
    def test_positive_move(self):
        spct, pchg, nsp, old_val, new_val, gain = calc_beta_impact(5.0, 1000.0, 10, 1.2)
        assert spct == pytest.approx(6.0)
        assert pchg == pytest.approx(60.0)
        assert nsp  == pytest.approx(1060.0)
        assert gain == pytest.approx(600.0)

    def test_negative_move(self):
        spct, pchg, nsp, *_ = calc_beta_impact(-3.0, 500.0, 5, 1.0)
        assert spct == pytest.approx(-3.0)
        assert pchg == pytest.approx(-15.0)
        assert nsp  == pytest.approx(485.0)

    def test_zero_nifty(self):
        spct, pchg, nsp, old_val, new_val, gain = calc_beta_impact(0.0, 200.0, 10, 1.5)
        assert gain == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# safe_sort
# ---------------------------------------------------------------------------

class TestSafeSort:
    def _df(self):
        return pd.DataFrame({"val": [30, 10, "N/A", 20], "label": list("abcd")})

    def test_ascending(self):
        df = self._df()
        result = safe_sort(df, "val", ascending=True)
        numeric_vals = pd.to_numeric(result["val"], errors="coerce").dropna().tolist()
        assert numeric_vals == sorted(numeric_vals)

    def test_descending(self):
        df = self._df()
        result = safe_sort(df, "val", ascending=False)
        numeric_vals = pd.to_numeric(result["val"], errors="coerce").dropna().tolist()
        assert numeric_vals == sorted(numeric_vals, reverse=True)

    def test_invalid_col_returns_df(self):
        df = self._df()
        result = safe_sort(df, "nonexistent_col")
        assert len(result) == len(df)
