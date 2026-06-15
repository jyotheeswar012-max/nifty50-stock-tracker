"""Tests for utils/constants.py structure and chart builder helpers."""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from utils.constants import NIFTY50, NSE_INDICES, SYMBOLS, FAMOUS_DATES, CACHE_TTL, REFRESH_MS
from utils.charts import build_price_chart, build_pct_bar, build_closing_bar, build_trend_chart


# ===========================================================================
# NIFTY50 constant validation
# ===========================================================================
class TestNifty50Constant:
    def test_has_exactly_50_entries(self):
        assert len(NIFTY50) == 50

    def test_all_entries_have_required_keys(self):
        for s in NIFTY50:
            for key in ("symbol", "name", "sector", "beta"):
                assert key in s, f"{s} missing '{key}'"

    def test_all_symbols_end_with_ns(self):
        for s in NIFTY50:
            assert s["symbol"].endswith(".NS"), f"{s['symbol']} does not end with .NS"

    def test_all_betas_are_positive_floats(self):
        for s in NIFTY50:
            assert isinstance(s["beta"], (int, float))
            assert s["beta"] > 0, f"{s['name']} beta={s['beta']}"

    def test_no_duplicate_symbols(self):
        syms = [s["symbol"] for s in NIFTY50]
        assert len(syms) == len(set(syms))

    def test_no_duplicate_names(self):
        names = [s["name"] for s in NIFTY50]
        assert len(names) == len(set(names))

    def test_symbols_list_matches_nifty50(self):
        assert SYMBOLS == [s["symbol"] for s in NIFTY50]

    def test_sector_is_non_empty_string(self):
        for s in NIFTY50:
            assert isinstance(s["sector"], str) and len(s["sector"]) > 0


# ===========================================================================
# NSE_INDICES constant
# ===========================================================================
class TestNseIndices:
    def test_has_at_least_one_index(self):
        assert len(NSE_INDICES) >= 1

    def test_all_entries_have_symbol_name_color(self):
        for idx in NSE_INDICES:
            for key in ("symbol", "name", "color"):
                assert key in idx

    def test_nifty50_index_present(self):
        symbols = [i["symbol"] for i in NSE_INDICES]
        assert "^NSEI" in symbols

    def test_color_is_hex_string(self):
        for idx in NSE_INDICES:
            assert idx["color"].startswith("#"), f"{idx['name']} color not a hex string"


# ===========================================================================
# FAMOUS_DATES constant
# ===========================================================================
class TestFamousDates:
    def test_is_dict(self):
        assert isinstance(FAMOUS_DATES, dict)

    def test_all_values_are_date_objects(self):
        from datetime import date
        for k, v in FAMOUS_DATES.items():
            assert isinstance(v, date), f"{k} has non-date value: {v}"

    def test_covid_crash_present(self):
        assert any("COVID" in k for k in FAMOUS_DATES)


# ===========================================================================
# Cache / refresh config
# ===========================================================================
class TestTimingConstants:
    def test_cache_ttl_is_positive(self):
        assert CACHE_TTL > 0

    def test_refresh_ms_is_positive(self):
        assert REFRESH_MS > 0

    def test_refresh_ms_at_least_1000ms(self):
        assert REFRESH_MS >= 1_000


# ===========================================================================
# build_price_chart
# ===========================================================================
class TestBuildPriceChart:
    def test_returns_figure(self, sample_ohlcv):
        import plotly.graph_objects as go
        fig = build_price_chart(sample_ohlcv, "Nifty 50", "3mo", "Line")
        assert isinstance(fig, go.Figure)

    def test_candlestick_type(self, sample_ohlcv):
        import plotly.graph_objects as go
        fig = build_price_chart(sample_ohlcv, "Nifty 50", "3mo", "Candlestick")
        assert isinstance(fig, go.Figure)

    def test_area_type(self, sample_ohlcv):
        import plotly.graph_objects as go
        fig = build_price_chart(sample_ohlcv, "Nifty 50", "3mo", "Area")
        assert isinstance(fig, go.Figure)

    def test_empty_df_returns_figure(self):
        import plotly.graph_objects as go
        fig = build_price_chart(pd.DataFrame(), "X", "1mo", "Line")
        assert isinstance(fig, go.Figure)

    def test_has_at_least_one_trace(self, sample_ohlcv):
        fig = build_price_chart(sample_ohlcv, "Nifty 50", "3mo", "Line")
        assert len(fig.data) >= 1

    def test_custom_height_applied(self, sample_ohlcv):
        fig = build_price_chart(sample_ohlcv, "X", "1mo", "Line", height=600)
        assert fig.layout.height == 600


# ===========================================================================
# build_pct_bar
# ===========================================================================
class TestBuildPctBar:
    @pytest.fixture
    def pct_df(self):
        return pd.DataFrame({
            "Symbol": ["RELIANCE", "INFY", "TCS", "HDFC"],
            "_pct":   [1.5, -0.8, 2.1, -1.2],
        })

    def test_returns_figure(self, pct_df):
        import plotly.graph_objects as go
        fig = build_pct_bar(pct_df, "Symbol", "_pct", "% Change")
        assert isinstance(fig, go.Figure)

    def test_has_one_trace(self, pct_df):
        fig = build_pct_bar(pct_df, "Symbol", "_pct", "% Change")
        assert len(fig.data) == 1

    def test_custom_height(self, pct_df):
        fig = build_pct_bar(pct_df, "Symbol", "_pct", "% Change", height=500)
        assert fig.layout.height == 500


# ===========================================================================
# build_trend_chart
# ===========================================================================
class TestBuildTrendChart:
    def test_empty_series_returns_figure(self):
        import plotly.graph_objects as go
        fig = build_trend_chart({})
        assert isinstance(fig, go.Figure)

    def test_single_series(self, sample_ohlcv):
        import plotly.graph_objects as go
        series = {"Nifty 50": {"df": sample_ohlcv, "color": "#6366f1"}}
        fig = build_trend_chart(series)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

    def test_multiple_series(self, sample_ohlcv):
        import plotly.graph_objects as go
        series = {
            "Series A": {"df": sample_ohlcv, "color": "#6366f1"},
            "Series B": {"df": sample_ohlcv, "color": "#10b981"},
        }
        fig = build_trend_chart(series)
        # hline + 2 scatter traces
        assert len(fig.data) >= 2

    def test_series_with_no_close_column_skipped(self):
        import plotly.graph_objects as go
        df_no_close = pd.DataFrame({"Open": [1, 2], "Volume": [100, 200]})
        series = {"Bad": {"df": df_no_close, "color": "#fff"}}
        fig = build_trend_chart(series)
        assert isinstance(fig, go.Figure)   # should not crash

    def test_series_with_empty_df_skipped(self):
        import plotly.graph_objects as go
        series = {"Empty": {"df": pd.DataFrame(), "color": "#fff"}}
        fig = build_trend_chart(series)
        assert isinstance(fig, go.Figure)
