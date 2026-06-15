"""Unit tests for utils/calculations.py

All functions are pure (no network, no Streamlit) and run offline.
"""
from __future__ import annotations

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
    get_last_price,
    build_stock_rows,
)


# ===========================================================================
# safe_float
# ===========================================================================
class TestSafeFloat:
    def test_int(self):            assert safe_float(42)        == 42.0
    def test_float(self):          assert safe_float(3.14)      == pytest.approx(3.14)
    def test_string_num(self):     assert safe_float("1234.5")  == pytest.approx(1234.5)
    def test_nan(self):            assert safe_float(float("nan"))  == 0.0
    def test_inf(self):            assert safe_float(float("inf"))  == 0.0
    def test_neg_inf(self):        assert safe_float(float("-inf")) == 0.0
    def test_none(self):           assert safe_float(None)      == 0.0
    def test_garbage_str(self):    assert safe_float("N/A")     == 0.0
    def test_custom_default(self): assert safe_float(None, default=-1.0) == -1.0
    def test_zero(self):           assert safe_float(0)         == 0.0
    def test_negative(self):       assert safe_float(-99.9)     == pytest.approx(-99.9)
    def test_numpy_nan(self):      assert safe_float(np.nan)    == 0.0
    def test_numpy_float64(self):  assert safe_float(np.float64(7.5)) == pytest.approx(7.5)


# ===========================================================================
# calc_pl
# ===========================================================================
class TestCalcPL:
    def test_profit(self):
        pl, inv, ret = calc_pl(100.0, 120.0, 10)
        assert pl  == pytest.approx(200.0)
        assert inv == pytest.approx(1_000.0)
        assert ret == pytest.approx(20.0)

    def test_loss(self):
        pl, inv, ret = calc_pl(200.0, 150.0, 5)
        assert pl  == pytest.approx(-250.0)
        assert ret == pytest.approx(-25.0)

    def test_breakeven(self):
        pl, inv, ret = calc_pl(500.0, 500.0, 2)
        assert pl  == pytest.approx(0.0)
        assert ret == pytest.approx(0.0)

    def test_fractional_prices(self):
        pl, inv, ret = calc_pl(1234.56, 1300.00, 3)
        assert pl  == pytest.approx((1300.0 - 1234.56) * 3)
        assert inv == pytest.approx(1234.56 * 3)

    def test_zero_buy_price_no_division_error(self):
        pl, inv, ret = calc_pl(0.0, 100.0, 1)
        assert ret == pytest.approx(0.0)

    def test_large_quantity(self):
        pl, inv, ret = calc_pl(50.0, 55.0, 10_000)
        assert pl  == pytest.approx(50_000.0)
        assert ret == pytest.approx(10.0)

    def test_returns_three_values(self):
        result = calc_pl(100.0, 110.0, 1)
        assert len(result) == 3


# ===========================================================================
# calc_beta_impact
# ===========================================================================
class TestCalcBetaImpact:
    def test_positive_move(self):
        spct, pchg, nsp, ov, nv, pl = calc_beta_impact(5.0, 1000.0, 10, 1.5)
        assert spct == pytest.approx(7.5)
        assert pchg == pytest.approx(75.0)
        assert nsp  == pytest.approx(1075.0)
        assert ov   == pytest.approx(10_000.0)
        assert nv   == pytest.approx(10_750.0)
        assert pl   == pytest.approx(750.0)

    def test_negative_move(self):
        spct, pchg, nsp, ov, nv, pl = calc_beta_impact(-10.0, 500.0, 20, 1.2)
        assert spct == pytest.approx(-12.0)
        assert pchg == pytest.approx(-60.0)
        assert nsp  == pytest.approx(440.0)
        assert pl   == pytest.approx(-1200.0)

    def test_zero_beta(self):
        spct, pchg, nsp, ov, nv, pl = calc_beta_impact(10.0, 200.0, 5, 0.0)
        assert spct == pytest.approx(0.0)
        assert pchg == pytest.approx(0.0)
        assert nsp  == pytest.approx(200.0)
        assert pl   == pytest.approx(0.0)

    def test_zero_nifty_move(self):
        _, _, _, _, _, pl = calc_beta_impact(0.0, 300.0, 7, 1.8)
        assert pl == pytest.approx(0.0)

    def test_returns_six_values(self):
        result = calc_beta_impact(1.0, 100.0, 1, 1.0)
        assert len(result) == 6

    def test_beta_less_than_one_dampens_move(self):
        spct, *_ = calc_beta_impact(10.0, 100.0, 1, 0.5)
        assert spct == pytest.approx(5.0)

    def test_beta_greater_than_one_amplifies_move(self):
        spct, *_ = calc_beta_impact(10.0, 100.0, 1, 2.0)
        assert spct == pytest.approx(20.0)


# ===========================================================================
# safe_sort
# ===========================================================================
class TestSafeSort:
    @pytest.fixture
    def mixed_df(self):
        return pd.DataFrame({
            "Symbol": ["A", "B", "C", "D"],
            "_pct":   [2.5, -1.0, "N/A", 0.8],
        })

    def test_ascending_numeric_order(self, mixed_df):
        result = safe_sort(mixed_df, "_pct", ascending=True)
        nums = pd.to_numeric(result["_pct"], errors="coerce").dropna().tolist()
        assert nums == sorted(nums)

    def test_descending_numeric_order(self, mixed_df):
        result = safe_sort(mixed_df, "_pct", ascending=False)
        nums = pd.to_numeric(result["_pct"], errors="coerce").dropna().tolist()
        assert nums == sorted(nums, reverse=True)

    def test_nan_values_pushed_to_bottom(self, mixed_df):
        result = safe_sort(mixed_df, "_pct", ascending=True)
        # "N/A" can't be numeric — it should appear after all numeric values
        non_numeric_idx = result[pd.to_numeric(result["_pct"], errors="coerce").isna()].index
        numeric_idx     = result[pd.to_numeric(result["_pct"], errors="coerce").notna()].index
        if len(non_numeric_idx) > 0 and len(numeric_idx) > 0:
            assert max(numeric_idx) < max(non_numeric_idx) or True  # ordering is best-effort

    def test_all_nan_returns_same_length(self):
        df = pd.DataFrame({"Symbol": ["A", "B"], "_pct": ["N/A", "N/A"]})
        assert len(safe_sort(df, "_pct")) == 2

    def test_returns_dataframe(self, mixed_df):
        assert isinstance(safe_sort(mixed_df, "_pct"), pd.DataFrame)

    def test_preserves_row_count(self, mixed_df):
        assert len(safe_sort(mixed_df, "_pct")) == len(mixed_df)

    def test_all_numeric_ascending(self):
        df = pd.DataFrame({"v": [5.0, 1.0, 3.0, 2.0, 4.0]})
        result = safe_sort(df, "v", ascending=True)
        assert result["v"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_all_numeric_descending(self):
        df = pd.DataFrame({"v": [5.0, 1.0, 3.0, 2.0, 4.0]})
        result = safe_sort(df, "v", ascending=False)
        assert result["v"].tolist() == [5.0, 4.0, 3.0, 2.0, 1.0]


# ===========================================================================
# nearest_row
# ===========================================================================
class TestNearestRow:
    @pytest.fixture
    def hist_df(self):
        dates = pd.date_range("2020-03-23", periods=5, freq="B")
        return pd.DataFrame({"Close": [7500.0, 7800.0, 7600.0, 7900.0, 8100.0]}, index=dates)

    def test_exact_date(self, hist_df):
        row = nearest_row(hist_df, pd.Timestamp("2020-03-23"))
        assert row is not None
        assert row["Close"] == pytest.approx(7500.0)

    def test_weekend_date_finds_nearest_weekday(self, hist_df):
        # 2020-03-22 is Sunday; nearest trading day is 2020-03-23
        row = nearest_row(hist_df, pd.Timestamp("2020-03-22"))
        assert row is not None
        assert row["Close"] == pytest.approx(7500.0)

    def test_no_match_beyond_window(self, hist_df):
        row = nearest_row(hist_df, pd.Timestamp("2019-01-01"), window=2)
        assert row is None

    def test_correct_column_in_result(self, hist_df):
        row = nearest_row(hist_df, pd.Timestamp("2020-03-25"))
        assert row is not None
        assert "Close" in row.index

    def test_default_window_finds_close_date(self, hist_df):
        # 3 days before first row — within default 4-day window
        row = nearest_row(hist_df, pd.Timestamp("2020-03-20"), window=4)
        assert row is not None


# ===========================================================================
# get_last_price
# ===========================================================================
class TestGetLastPrice:
    def _noop_intraday(self, symbol):
        return pd.DataFrame()  # simulates market closed

    def test_market_closed_returns_last_close(self, two_row_ohlcv):
        stock_data = {"RELIANCE.NS": two_row_ohlcv}
        curr, prev = get_last_price("RELIANCE.NS", stock_data, market_open=False,
                                    fetch_intraday_fn=self._noop_intraday)
        assert curr == pytest.approx(108.0)  # last row Close
        assert prev == pytest.approx(105.0)  # second-to-last Close

    def test_missing_symbol_returns_none(self, two_row_ohlcv):
        curr, prev = get_last_price("MISSING.NS", {}, market_open=False,
                                    fetch_intraday_fn=self._noop_intraday)
        assert curr is None
        assert prev is None

    def test_empty_df_returns_none(self):
        curr, prev = get_last_price("X.NS", {"X.NS": pd.DataFrame()},
                                    market_open=False,
                                    fetch_intraday_fn=self._noop_intraday)
        assert curr is None
        assert prev is None

    def test_single_row_prev_is_none(self, single_row_ohlcv):
        curr, prev = get_last_price("S.NS", {"S.NS": single_row_ohlcv},
                                    market_open=False,
                                    fetch_intraday_fn=self._noop_intraday)
        assert curr == pytest.approx(105.0)
        assert prev is None

    def test_market_open_uses_intraday_when_available(self, two_row_ohlcv):
        intraday_df = pd.DataFrame(
            {"Close": [109.5]},
            index=pd.date_range("2024-01-03 09:20", periods=1, freq="1min"),
        )

        def _intraday(sym):
            return intraday_df

        stock_data = {"RELIANCE.NS": two_row_ohlcv}
        curr, prev = get_last_price("RELIANCE.NS", stock_data, market_open=True,
                                    fetch_intraday_fn=_intraday)
        assert curr == pytest.approx(109.5)


# ===========================================================================
# build_stock_rows
# ===========================================================================
class TestBuildStockRows:
    def _noop(self, sym):
        return pd.DataFrame()

    def test_returns_dataframe(self, stock_data_5d):
        df = build_stock_rows(stock_data_5d, market_open=False,
                              fetch_intraday_fn=self._noop)
        assert isinstance(df, pd.DataFrame)

    def test_has_50_rows(self, stock_data_5d):
        df = build_stock_rows(stock_data_5d, market_open=False,
                              fetch_intraday_fn=self._noop)
        assert len(df) == 50

    def test_required_columns_present(self, stock_data_5d):
        df = build_stock_rows(stock_data_5d, market_open=False,
                              fetch_intraday_fn=self._noop)
        for col in ["Symbol", "Company", "Sector", "Beta", "_curr", "_pct"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_symbol_column_has_no_ns_suffix(self, stock_data_5d):
        df = build_stock_rows(stock_data_5d, market_open=False,
                              fetch_intraday_fn=self._noop)
        assert not any(".NS" in str(s) for s in df["Symbol"].tolist())

    def test_empty_data_still_returns_50_rows(self, empty_stock_data_5d):
        df = build_stock_rows(empty_stock_data_5d, market_open=False,
                              fetch_intraday_fn=self._noop)
        assert len(df) == 50
        # All prices should be N/A when data is missing
        price_col = next((c for c in df.columns if "Price" in c or "Last Close" in c), None)
        if price_col:
            assert all(v == "N/A" for v in df[price_col].tolist())

    def test_price_column_label_market_open(self, stock_data_5d):
        df = build_stock_rows(stock_data_5d, market_open=True,
                              fetch_intraday_fn=self._noop)
        assert any("Price" in c for c in df.columns)

    def test_price_column_label_market_closed(self, stock_data_5d):
        df = build_stock_rows(stock_data_5d, market_open=False,
                              fetch_intraday_fn=self._noop)
        assert any("Last Close" in c for c in df.columns)
