"""Shared pytest fixtures for the NSE Nifty50 Tracker test suite.

All external I/O (yfinance, nselib, Streamlit cache) is mocked here
so every test runs offline in < 1 second.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Core OHLCV fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_ohlcv() -> pd.DataFrame:
    """30 business-day OHLCV DataFrame with DatetimeIndex (no timezone)."""
    np.random.seed(42)
    dates  = pd.date_range("2024-01-02", periods=30, freq="B")
    close  = 21_000 + np.cumsum(np.random.randn(30) * 50)
    df = pd.DataFrame(
        {
            "Open":   close - 20,
            "High":   close + 40,
            "Low":    close - 40,
            "Close":  close,
            "Volume": np.random.randint(100_000, 500_000, 30).astype(float),
        },
        index=dates,
    )
    df.index.name = "Date"
    return df


@pytest.fixture(scope="session")
def single_row_ohlcv() -> pd.DataFrame:
    """Single-row OHLCV — exercises edge-cases in prev-close logic."""
    return pd.DataFrame(
        {"Open": [100.0], "High": [110.0], "Low": [95.0], "Close": [105.0], "Volume": [50_000.0]},
        index=pd.date_range("2024-01-02", periods=1, freq="B"),
    )


@pytest.fixture(scope="session")
def two_row_ohlcv() -> pd.DataFrame:
    """Two-row OHLCV — minimum needed for curr/prev price pair."""
    return pd.DataFrame(
        {
            "Open":   [100.0, 105.0],
            "High":   [110.0, 115.0],
            "Low":    [95.0, 100.0],
            "Close":  [105.0, 108.0],
            "Volume": [10_000.0, 12_000.0],
        },
        index=pd.date_range("2024-01-02", periods=2, freq="B"),
    )


@pytest.fixture(scope="session")
def multiindex_ohlcv() -> pd.DataFrame:
    """yfinance-style MultiIndex column DataFrame (batch download shape)."""
    np.random.seed(0)
    dates  = pd.date_range("2024-01-02", periods=5, freq="B")
    close  = 22_000 + np.arange(5) * 50.0
    df = pd.DataFrame(
        [
            {("Open", ""): c - 10, ("High", ""): c + 20,
             ("Low", ""): c - 20, ("Close", ""): c, ("Volume", ""): 200_000.0}
            for c in close
        ],
        index=dates,
    )
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


# ---------------------------------------------------------------------------
# Mock yfinance Ticker
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ticker(sample_ohlcv):
    """Mocked yfinance.Ticker that returns sample_ohlcv from .history()."""
    t = MagicMock()
    t.history.return_value = sample_ohlcv.copy()
    t.info = {
        "longName": "Reliance Industries Limited",
        "regularMarketPrice": 2800.0,
        "fiftyTwoWeekHigh": 3100.0,
        "fiftyTwoWeekLow": 2200.0,
        "marketCap": 18_000_000_000_000,
    }
    return t


@pytest.fixture
def mock_ticker_empty():
    """Mocked yfinance.Ticker that returns an empty DataFrame."""
    t = MagicMock()
    t.history.return_value = pd.DataFrame()
    t.info = {}
    return t


# ---------------------------------------------------------------------------
# stock_data_5d dict (used by calculations helpers)
# ---------------------------------------------------------------------------

@pytest.fixture
def stock_data_5d(two_row_ohlcv):
    """Minimal stock_data_5d dict for get_last_price / build_stock_rows."""
    from utils.constants import NIFTY50
    return {s["symbol"]: two_row_ohlcv.copy() for s in NIFTY50}


@pytest.fixture
def empty_stock_data_5d():
    """stock_data_5d where every symbol maps to an empty DataFrame."""
    from utils.constants import NIFTY50
    return {s["symbol"]: pd.DataFrame() for s in NIFTY50}


# ---------------------------------------------------------------------------
# Patch Streamlit cache for unit tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_streamlit_cache(monkeypatch):
    """
    Replace @st.cache_data with a no-op so cached functions can be
    called without a running Streamlit server.
    """
    import streamlit as st
    monkeypatch.setattr(st, "cache_data", lambda *a, **kw: lambda fn: fn)
    monkeypatch.setattr(st, "session_state", {}, raising=False)
