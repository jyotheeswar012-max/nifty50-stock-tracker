"""Tests for the multi-source fallback logic in utils/data.py.

All network I/O is mocked so these run fully offline in CI.
"""
from unittest.mock import patch
import pandas as pd
import pytest

DATE_IDX = pd.date_range("2024-01-01", periods=3, freq="B")

def _good_df():
    return pd.DataFrame(
        {"Open": [100.0, 101.0, 102.0],
         "High": [105.0, 106.0, 107.0],
         "Low":  [ 98.0,  99.0, 100.0],
         "Close":[103.0, 104.0, 105.0],
         "Volume":[1000,  1100,  1200]},
        index=DATE_IDX,
    )


class TestValidateOhlcv:
    def test_valid_df_returns_true(self):
        from utils.data import _validate_ohlcv
        assert _validate_ohlcv(_good_df()) is True

    def test_empty_df_returns_false(self):
        from utils.data import _validate_ohlcv
        assert _validate_ohlcv(pd.DataFrame()) is False

    def test_missing_close_returns_false(self):
        from utils.data import _validate_ohlcv
        df = _good_df().drop(columns=["Close"])
        assert _validate_ohlcv(df) is False

    def test_none_returns_false(self):
        from utils.data import _validate_ohlcv
        assert _validate_ohlcv(None) is False


class TestCleanDf:
    def test_strips_timezone(self):
        from utils.data import _clean_df
        df = _good_df()
        df.index = pd.DatetimeIndex(df.index).tz_localize("Asia/Kolkata")
        result = _clean_df(df)
        assert result.index.tz is None

    def test_empty_input_returns_empty(self):
        from utils.data import _clean_df
        assert _clean_df(pd.DataFrame()).empty

    def test_normalizes_date_index(self):
        from utils.data import _clean_df
        result = _clean_df(_good_df())
        assert all(t.hour == 0 and t.minute == 0 for t in result.index)


class TestFetchWithFallback:
    def test_yfinance_success_no_fallback_needed(self):
        from utils import data as d
        d._STALE_STORE.clear()
        good = _good_df()
        with patch.object(d, "_yf_history",     return_value=good), \
             patch.object(d, "_nselib_history", return_value=pd.DataFrame()) as nselib_mock:
            result = d._fetch_with_fallback("TEST.NS", "3mo")
        nselib_mock.assert_not_called()
        assert not result.empty

    def test_nselib_called_when_yfinance_fails(self):
        from utils import data as d
        d._STALE_STORE.clear()
        good = _good_df()
        with patch.object(d, "_yf_history",     return_value=pd.DataFrame()), \
             patch.object(d, "_nselib_history", return_value=good):
            result = d._fetch_with_fallback("TEST.NS", "3mo")
        assert not result.empty

    def test_stale_cache_used_when_both_fail(self):
        from utils import data as d
        key = "STALE.NS:3mo"
        d._STALE_STORE[key] = _good_df()
        with patch.object(d, "_yf_history",     return_value=pd.DataFrame()), \
             patch.object(d, "_nselib_history", return_value=pd.DataFrame()):
            result = d._fetch_with_fallback("STALE.NS", "3mo")
        assert not result.empty
        d._STALE_STORE.pop(key, None)

    def test_empty_when_all_sources_fail_and_no_cache(self):
        from utils import data as d
        d._STALE_STORE.pop("GHOST.NS:3mo", None)
        with patch.object(d, "_yf_history",     return_value=pd.DataFrame()), \
             patch.object(d, "_nselib_history", return_value=pd.DataFrame()):
            result = d._fetch_with_fallback("GHOST.NS", "3mo")
        assert result.empty

    def test_stale_cache_populated_on_success(self):
        from utils import data as d
        d._STALE_STORE.pop("POP.NS:3mo", None)
        good = _good_df()
        with patch.object(d, "_yf_history",     return_value=good), \
             patch.object(d, "_nselib_history", return_value=pd.DataFrame()):
            d._fetch_with_fallback("POP.NS", "3mo")
        assert "POP.NS:3mo" in d._STALE_STORE
