"""Unit tests for utils/calculations.py

All functions here are pure (no network, no Streamlit) so they run in CI
without any mocking of external services.
"""
import math
import pandas as pd
import numpy as np
import pytest

from utils.calculations import (
    safe_float,
    calc_pl,
    calc_beta_impact,
    safe_sort,
    nearest_row,
)


# ---------------------------------------------------------------------------
# safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_normal_int(self):
        assert safe_float(42) == 42.0

    def test_normal_float(self):
        assert safe_float(3.14) == pytest.approx(3.14)

    def test_string_number(self):
        assert safe_float("1234.5") == pytest.approx(1234.5)

    def test_nan_returns_default(self):
        assert safe_float(float("nan")) == 0.0

    def test_inf_returns_default(self):
        assert safe_float(float("inf")) == 0.0

    def test_neg_inf_returns_default(self):
        assert safe_float(float("-inf")) == 0.0

    def test_none_returns_default(self):
        assert safe_float(None) == 0.0

    def test_string_garbage_returns_default(self):
        assert safe_float("N/A") == 0.0

    def test_custom_default(self):
        assert safe_float(None, default=-1.0) == -1.0

    def test_zero_is_valid(self):
        assert safe_float(0) == 0.0

    def test_negative_number(self):
        assert safe_float(-99.9) == pytest.approx(-99.9)


# ---------------------------------------------------------------------------
# calc_pl
# ---------------------------------------------------------------------------

class TestCalcPL:
    def test_profit(self):
        pl, inv, ret = calc_pl(buy_price=100.0, sell_price=120.0, qty=10)
        assert pl  == pytest.approx(200.0)
        assert inv == pytest.approx(1000.0)
        assert ret == pytest.approx(20.0)

    def test_loss(self):
        pl, inv, ret = calc_pl(buy_price=200.0, sell_price=150.0, qty=5)
        assert pl  == pytest.approx(-250.0)
        assert inv == pytest.approx(1000.0)
        assert ret == pytest.approx(-25.0)

    def test_no_change(self):
        pl, inv, ret = calc_pl(buy_price=500.0, sell_price=500.0, qty=2)
        assert pl  == pytest.approx(0.0)
        assert inv == pytest.approx(1000.0)
        assert ret == pytest.approx(0.0)

    def test_fractional_prices(self):
        pl, inv, ret = calc_pl(buy_price=1234.56, sell_price=1300.00, qty=3)
        assert pl  == pytest.approx((1300.0 - 1234.56) * 3)
        assert inv == pytest.approx(1234.56 * 3)

    def test_zero_investment_returns_zero_pct(self):
        # Edge: buy_price=0 should not raise ZeroDivisionError
        pl, inv, ret = calc_pl(buy_price=0, sell_price=100, qty=1)
        assert ret == pytest.approx(0.0)

    def test_large_quantity(self):
        pl, inv, ret = calc_pl(buy_price=50.0, sell_price=55.0, qty=10_000)
        assert pl  == pytest.approx(50_000.0)
        assert ret == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# calc_beta_impact
# ---------------------------------------------------------------------------

class TestCalcBetaImpact:
    def test_positive_nifty_move(self):
        spct, pchg, nsp, ov, nv, pl = calc_beta_impact(
            nifty_pct=5.0, stock_price=1000.0, qty=10, beta=1.5
        )
        assert spct == pytest.approx(7.5)          # 5 * 1.5
        assert pchg == pytest.approx(75.0)         # 1000 * 0.075
        assert nsp  == pytest.approx(1075.0)       # 1000 + 75
        assert ov   == pytest.approx(10_000.0)     # 1000 * 10
        assert nv   == pytest.approx(10_750.0)     # 1075 * 10
        assert pl   == pytest.approx(750.0)        # 75 * 10

    def test_negative_nifty_move(self):
        spct, pchg, nsp, ov, nv, pl = calc_beta_impact(
            nifty_pct=-10.0, stock_price=500.0, qty=20, beta=1.2
        )
        assert spct == pytest.approx(-12.0)
        assert pchg == pytest.approx(-60.0)
        assert nsp  == pytest.approx(440.0)
        assert pl   == pytest.approx(-1200.0)

    def test_zero_beta(self):
        spct, pchg, nsp, ov, nv, pl = calc_beta_impact(
            nifty_pct=10.0, stock_price=200.0, qty=5, beta=0.0
        )
        assert spct == pytest.approx(0.0)
        assert pchg == pytest.approx(0.0)
        assert nsp  == pytest.approx(200.0)
        assert pl   == pytest.approx(0.0)

    def test_zero_nifty_move(self):
        spct, pchg, nsp, ov, nv, pl = calc_beta_impact(
            nifty_pct=0.0, stock_price=300.0, qty=7, beta=1.8
        )
        assert pl == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# safe_sort
# ---------------------------------------------------------------------------

class TestSafeSort:
    def _make_df(self):
        return pd.DataFrame({
            "Symbol": ["A", "B", "C", "D"],
            "_pct":   [2.5, -1.0, "N/A", 0.8],
        })

    def test_ascending(self):
        df = self._make_df()
        result = safe_sort(df, "_pct", ascending=True)
        nums = pd.to_numeric(result["_pct"], errors="coerce").dropna().tolist()
        assert nums == sorted(nums)

    def test_descending(self):
        df = self._make_df()
        result = safe_sort(df, "_pct", ascending=False)
        nums = pd.to_numeric(result["_pct"], errors="coerce").dropna().tolist()
        assert nums == sorted(nums, reverse=True)

    def test_all_nan_column_returns_original_shape(self):
        df = pd.DataFrame({"Symbol": ["A", "B"], "_pct": ["N/A", "N/A"]})
        result = safe_sort(df, "_pct")
        assert len(result) == 2

    def test_returns_dataframe(self):
        df = self._make_df()
        assert isinstance(safe_sort(df, "_pct"), pd.DataFrame)


# ---------------------------------------------------------------------------
# nearest_row
# ---------------------------------------------------------------------------

class TestNearestRow:
    def _make_df(self):
        dates = pd.date_range("2020-03-23", periods=5, freq="B")  # business days
        df = pd.DataFrame({"Close": [7500, 7800, 7600, 7900, 8100]}, index=dates)
        return df

    def test_exact_date_match(self):
        df  = self._make_df()
        row = nearest_row(df, pd.Timestamp("2020-03-23"))
        assert row is not None
        assert row["Close"] == 7500

    def test_one_day_offset(self):
        df  = self._make_df()
        # 2020-03-22 is a Sunday; nearest should find 2020-03-23
        row = nearest_row(df, pd.Timestamp("2020-03-22"))
        assert row is not None
        assert row["Close"] == 7500

    def test_no_match_beyond_window(self):
        df  = self._make_df()
        # A date far from any row and beyond the default 4-day window
        row = nearest_row(df, pd.Timestamp("2019-01-01"), window=2)
        assert row is None

    def test_returns_correct_columns(self):
        df  = self._make_df()
        row = nearest_row(df, pd.Timestamp("2020-03-25"))
        assert row is not None
        assert "Close" in row.index
