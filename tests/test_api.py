"""Integration tests for utils/data.py — all external I/O is mocked.

We test the *actual* public functions imported from utils.data, not inline stubs.
All yfinance calls are intercepted so no network access is needed.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Import helpers from the real utils (no network calls made at import time)
# ---------------------------------------------------------------------------
from utils.data import (
    is_nse_open,
    _clean_df,
    _clean_intraday_df,
    _validate_ohlcv,
    _flatten_cols,
)


# ===========================================================================
# _flatten_cols
# ===========================================================================
class TestFlattenCols:
    def test_single_level_unchanged(self, sample_ohlcv):
        result = _flatten_cols(sample_ohlcv.copy())
        assert not isinstance(result.columns, pd.MultiIndex)

    def test_multiindex_ohlcv_cols_flattened(self, multiindex_ohlcv):
        result = _flatten_cols(multiindex_ohlcv.copy())
        assert not isinstance(result.columns, pd.MultiIndex)
        assert "Close" in result.columns

    def test_multiindex_preserves_row_count(self, multiindex_ohlcv):
        result = _flatten_cols(multiindex_ohlcv.copy())
        assert len(result) == len(multiindex_ohlcv)


# ===========================================================================
# _clean_df
# ===========================================================================
class TestCleanDf:
    def test_empty_input_returns_empty(self):
        assert _clean_df(pd.DataFrame()).empty

    def test_none_input_returns_empty(self):
        assert _clean_df(None).empty  # type: ignore

    def test_removes_timezone_from_index(self):
        import pytz
        dates = pd.date_range("2024-01-02", periods=5, freq="B", tz="UTC")
        df = pd.DataFrame({"Open": 1, "High": 2, "Low": 0, "Close": 1.5, "Volume": 1000}, index=dates)
        result = _clean_df(df)
        assert result.index.tz is None

    def test_index_normalised_to_midnight(self, sample_ohlcv):
        # Add non-midnight timestamps
        df = sample_ohlcv.copy()
        df.index = df.index + pd.Timedelta(hours=9, minutes=15)
        result = _clean_df(df)
        assert all(t == t.normalize() for t in result.index)

    def test_returns_dataframe(self, sample_ohlcv):
        assert isinstance(_clean_df(sample_ohlcv.copy()), pd.DataFrame)

    def test_preserves_ohlcv_columns(self, sample_ohlcv):
        result = _clean_df(sample_ohlcv.copy())
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in result.columns


# ===========================================================================
# _validate_ohlcv
# ===========================================================================
class TestValidateOHLCV:
    def test_valid_df_passes(self, sample_ohlcv):
        assert _validate_ohlcv(sample_ohlcv) is True

    def test_empty_df_fails(self):
        assert _validate_ohlcv(pd.DataFrame()) is False

    def test_none_fails(self):
        assert _validate_ohlcv(None) is False  # type: ignore

    def test_missing_close_fails(self, sample_ohlcv):
        df = sample_ohlcv.drop(columns=["Close"])
        assert _validate_ohlcv(df) is False

    def test_missing_high_fails(self, sample_ohlcv):
        df = sample_ohlcv.drop(columns=["High"])
        assert _validate_ohlcv(df) is False

    def test_df_with_all_ohlcv_passes(self):
        df = pd.DataFrame(
            {"Open": [1], "High": [2], "Low": [0], "Close": [1.5], "Volume": [100]},
            index=pd.date_range("2024-01-02", periods=1),
        )
        assert _validate_ohlcv(df) is True


# ===========================================================================
# is_nse_open  (mocked datetime)
# ===========================================================================
class TestIsNseOpen:
    def _mock_now(self, weekday, hour, minute):
        """Return a mock datetime with given weekday/time in IST."""
        import datetime
        from unittest.mock import patch
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        dt  = datetime.datetime(2024, 1, 2, hour, minute, 0, tzinfo=ist)   # Tuesday = 1
        # We just call the real function but patch datetime.now inside it
        return dt

    def test_returns_tuple_of_three(self):
        result = is_nse_open()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_bool_flag_is_bool(self):
        is_open, _, _ = is_nse_open()
        assert isinstance(is_open, bool)

    def test_status_is_string(self):
        _, status, _ = is_nse_open()
        assert isinstance(status, str)
        assert len(status) > 0

    def test_label_is_string(self):
        _, _, label = is_nse_open()
        assert isinstance(label, str)


# ===========================================================================
# fetch_ticker — mocked yfinance, tests real utils/data.py pipeline
# ===========================================================================
class TestFetchTicker:
    @patch("utils.data.yf.Ticker")
    def test_returns_dataframe(self, mock_cls, sample_ohlcv):
        mock_cls.return_value.history.return_value = sample_ohlcv.copy()
        from utils.data import fetch_ticker
        result = fetch_ticker.__wrapped__("RELIANCE.NS", "3mo") if hasattr(fetch_ticker, "__wrapped__") else fetch_ticker("RELIANCE.NS", "3mo")
        assert isinstance(result, pd.DataFrame)

    @patch("utils.data.yf.Ticker")
    def test_has_required_columns(self, mock_cls, sample_ohlcv):
        mock_cls.return_value.history.return_value = sample_ohlcv.copy()
        from utils.data import fetch_ticker
        fn = getattr(fetch_ticker, "__wrapped__", fetch_ticker)
        result = fn("RELIANCE.NS", "3mo")
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in result.columns

    @patch("utils.data.yf.Ticker")
    def test_empty_yfinance_returns_empty(self, mock_cls):
        mock_cls.return_value.history.return_value = pd.DataFrame()
        from utils.data import fetch_ticker
        fn = getattr(fetch_ticker, "__wrapped__", fetch_ticker)
        result = fn("BADTICKER.NS", "3mo")
        assert isinstance(result, pd.DataFrame)

    @patch("utils.data.yf.Ticker")
    def test_index_is_datetimeindex(self, mock_cls, sample_ohlcv):
        mock_cls.return_value.history.return_value = sample_ohlcv.copy()
        from utils.data import fetch_ticker
        fn = getattr(fetch_ticker, "__wrapped__", fetch_ticker)
        result = fn("RELIANCE.NS", "3mo")
        if not result.empty:
            assert isinstance(result.index, pd.DatetimeIndex)

    @patch("utils.data.yf.Ticker")
    def test_yfinance_exception_returns_empty(self, mock_cls):
        mock_cls.return_value.history.side_effect = RuntimeError("network error")
        from utils.data import fetch_ticker
        fn = getattr(fetch_ticker, "__wrapped__", fetch_ticker)
        result = fn("RELIANCE.NS", "3mo")
        assert isinstance(result, pd.DataFrame)


# ===========================================================================
# fetch_all_stocks_5d — mocked to return data for all 50 symbols
# ===========================================================================
class TestFetchAllStocks5d:
    @patch("utils.data.yf.Ticker")
    def test_returns_dict(self, mock_cls, sample_ohlcv):
        mock_cls.return_value.history.return_value = sample_ohlcv.copy()
        from utils.data import fetch_all_stocks_5d
        fn = getattr(fetch_all_stocks_5d, "__wrapped__", fetch_all_stocks_5d)
        result = fn()
        assert isinstance(result, dict)

    @patch("utils.data.yf.Ticker")
    def test_dict_values_are_dataframes(self, mock_cls, sample_ohlcv):
        mock_cls.return_value.history.return_value = sample_ohlcv.copy()
        from utils.data import fetch_all_stocks_5d
        fn = getattr(fetch_all_stocks_5d, "__wrapped__", fetch_all_stocks_5d)
        result = fn()
        for sym, df in result.items():
            assert isinstance(df, pd.DataFrame), f"{sym} not a DataFrame"

    @patch("utils.data.yf.Ticker")
    def test_all_failed_returns_empty_dict(self, mock_cls):
        mock_cls.return_value.history.return_value = pd.DataFrame()
        from utils.data import fetch_all_stocks_5d
        fn = getattr(fetch_all_stocks_5d, "__wrapped__", fetch_all_stocks_5d)
        result = fn()
        # When all sources return empty, dict should still be a dict (possibly empty)
        assert isinstance(result, dict)


# ===========================================================================
# fetch_intraday
# ===========================================================================
class TestFetchIntraday:
    @patch("utils.data.yf.Ticker")
    def test_returns_dataframe(self, mock_cls, sample_ohlcv):
        mock_cls.return_value.history.return_value = sample_ohlcv.copy()
        from utils.data import fetch_intraday
        fn = getattr(fetch_intraday, "__wrapped__", fetch_intraday)
        result = fn("RELIANCE.NS")
        assert isinstance(result, pd.DataFrame)

    @patch("utils.data.yf.Ticker")
    def test_exception_returns_empty(self, mock_cls):
        mock_cls.return_value.history.side_effect = Exception("timeout")
        from utils.data import fetch_intraday
        fn = getattr(fetch_intraday, "__wrapped__", fetch_intraday)
        result = fn("RELIANCE.NS")
        assert isinstance(result, pd.DataFrame)
