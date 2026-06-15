import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────

@pytest.fixture
def raw_price_data():
    """Simulate raw OHLCV data from yfinance/API."""
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    np.random.seed(42)
    close = 21000 + np.cumsum(np.random.randn(30) * 50)
    return pd.DataFrame({
        "Date": dates,
        "Open":  close - 20,
        "High":  close + 40,
        "Low":   close - 40,
        "Close": close,
        "Volume": np.random.randint(100_000, 500_000, 30),
    })


@pytest.fixture
def cleaned_price_data(raw_price_data):
    """Already-cleaned dataframe with DatetimeIndex."""
    df = raw_price_data.copy()
    df = df.set_index("Date")
    df.index = pd.to_datetime(df.index)
    df = df.dropna()
    return df


@pytest.fixture
def holdings_data():
    """Sample user portfolio holdings."""
    return pd.DataFrame({
        "symbol":         ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS"],
        "shares":         [10, 20, 15, 5],
        "avg_buy_price":  [2500.0, 1600.0, 1400.0, 3500.0],
        "current_price":  [2800.0, 1750.0, 1350.0, 3900.0],
    })


@pytest.fixture
def mock_yfinance_ticker(cleaned_price_data):
    """Mocked yfinance Ticker object."""
    ticker = MagicMock()
    ticker.history.return_value = cleaned_price_data
    ticker.info = {
        "longName": "Nifty 50 Index",
        "regularMarketPrice": 22500.0,
        "fiftyTwoWeekHigh": 23500.0,
        "fiftyTwoWeekLow": 18500.0,
        "marketCap": None,
    }
    return ticker
