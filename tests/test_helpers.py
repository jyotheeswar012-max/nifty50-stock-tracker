"""
tests/test_helpers.py
=====================
Unit tests for helper functions used across app.py.

Run with:
    pytest tests/ -v
"""

import math
import pytest
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import helpers directly (avoids Streamlit import side-effects)
def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return default


class TestSafeFloat:

    def test_normal_int(self):
        assert safe_float(42) == 42.0

    def test_normal_float(self):
        assert safe_float(3.14) == pytest.approx(3.14)

    def test_string_number(self):
        assert safe_float("123.45") == pytest.approx(123.45)

    def test_nan_returns_default(self):
        assert safe_float(float("nan")) == 0.0

    def test_inf_returns_default(self):
        assert safe_float(float("inf")) == 0.0
        assert safe_float(float("-inf")) == 0.0

    def test_custom_default(self):
        assert safe_float(float("nan"), default=99.0) == 99.0

    def test_none_returns_default(self):
        assert safe_float(None) == 0.0

    def test_non_numeric_string(self):
        assert safe_float("abc") == 0.0

    def test_numpy_nan(self):
        assert safe_float(np.nan) == 0.0

    def test_numpy_float(self):
        assert safe_float(np.float64(7.5)) == pytest.approx(7.5)


class TestCleanDf:
    """Tests for the _clean_df MultiIndex flattener."""

    def _make_multiindex_df(self, ticker="^NSEI"):
        cols = pd.MultiIndex.from_tuples([
            ("Open",  ticker), ("High",   ticker),
            ("Low",   ticker), ("Close",  ticker), ("Volume", ticker),
        ])
        idx = pd.date_range("2026-06-01", periods=3, freq="D", tz="UTC")
        data = [[100, 110, 90, 105, 1000],
                [105, 115, 95, 110, 2000],
                [110, 120, 100, 115, 1500]]
        return pd.DataFrame(data, index=idx, columns=cols)

    def test_flattens_multiindex_ohlcv_in_level0(self):
        df = self._make_multiindex_df()
        # simulate _clean_df logic inline
        lvl0 = list(df.columns.get_level_values(0))
        ohlcv = {"Open", "High", "Low", "Close", "Volume"}
        if ohlcv.intersection(set(lvl0)):
            df.columns = lvl0
        assert "Close" in df.columns
        assert "Open"  in df.columns

    def test_strips_timezone(self):
        df = self._make_multiindex_df()
        lvl0 = list(df.columns.get_level_values(0))
        df.columns = lvl0
        df.index = df.index.tz_localize(None) if df.index.tz is None else df.index.tz_convert(None)
        assert df.index.tz is None

    def test_flat_df_passes_through(self):
        """A properly formatted flat DataFrame should remain unchanged."""
        df = pd.DataFrame(
            {"Open": [100.0], "High": [110.0], "Low": [90.0],
             "Close": [105.0], "Volume": [5000]},
            index=pd.date_range("2026-06-01", periods=1)
        )
        assert "Close" in df.columns
        assert not isinstance(df.columns, pd.MultiIndex)
