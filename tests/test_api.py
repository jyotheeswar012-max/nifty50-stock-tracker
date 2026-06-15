"""Integration tests: data-fetching functions with mocked API calls."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ── inline data fetcher (mirrors your real utils/api.py) ──────────────────────

def fetch_nifty50_history(ticker_symbol: str = "^NSEI",
                          period: str = "1y") -> pd.DataFrame:
    import yfinance as yf
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


def fetch_ticker_info(ticker_symbol: str) -> dict:
    import yfinance as yf
    return yf.Ticker(ticker_symbol).info


def fetch_multiple_tickers(symbols: list, period: str = "1y") -> dict:
    import yfinance as yf
    result = {}
    for sym in symbols:
        df = yf.Ticker(sym).history(period=period)
        result[sym] = df
    return result


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestFetchNifty50History:
    @patch("yfinance.Ticker")
    def test_returns_dataframe(self, mock_ticker_cls, mock_yfinance_ticker, cleaned_price_data):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_nifty50_history("^NSEI", period="1y")
        assert isinstance(result, pd.DataFrame)

    @patch("yfinance.Ticker")
    def test_has_required_ohlcv_columns(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_nifty50_history("^NSEI")
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in result.columns

    @patch("yfinance.Ticker")
    def test_index_is_datetime(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_nifty50_history("^NSEI")
        assert isinstance(result.index, pd.DatetimeIndex)

    @patch("yfinance.Ticker")
    def test_data_is_sorted_ascending(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_nifty50_history("^NSEI")
        assert result.index.is_monotonic_increasing

    @patch("yfinance.Ticker")
    def test_no_nan_in_close(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_nifty50_history("^NSEI")
        assert result["Close"].isna().sum() == 0

    @patch("yfinance.Ticker")
    def test_close_prices_positive(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_nifty50_history("^NSEI")
        assert (result["Close"] > 0).all()

    @patch("yfinance.Ticker")
    def test_returns_non_empty_dataframe(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_nifty50_history("^NSEI")
        assert not result.empty


class TestFetchTickerInfo:
    @patch("yfinance.Ticker")
    def test_returns_dict(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_ticker_info("^NSEI")
        assert isinstance(result, dict)

    @patch("yfinance.Ticker")
    def test_contains_expected_keys(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_ticker_info("^NSEI")
        for key in ["longName", "regularMarketPrice", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]:
            assert key in result

    @patch("yfinance.Ticker")
    def test_current_price_is_float(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        result = fetch_ticker_info("^NSEI")
        assert isinstance(result["regularMarketPrice"], float)


class TestFetchMultipleTickers:
    @patch("yfinance.Ticker")
    def test_returns_dict_of_dataframes(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        symbols = ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS"]
        result = fetch_multiple_tickers(symbols)
        assert isinstance(result, dict)
        for sym in symbols:
            assert sym in result
            assert isinstance(result[sym], pd.DataFrame)

    @patch("yfinance.Ticker")
    def test_correct_number_of_tickers(self, mock_ticker_cls, mock_yfinance_ticker):
        mock_ticker_cls.return_value = mock_yfinance_ticker
        symbols = ["RELIANCE.NS", "HDFCBANK.NS"]
        result = fetch_multiple_tickers(symbols)
        assert len(result) == 2

    @patch("yfinance.Ticker")
    def test_empty_symbols_returns_empty_dict(self, mock_ticker_cls, mock_yfinance_ticker):
        result = fetch_multiple_tickers([])
        assert result == {}


class TestAPIEdgeCases:
    @patch("yfinance.Ticker")
    def test_empty_history_returns_empty_dataframe(self, mock_ticker_cls):
        ticker = MagicMock()
        ticker.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = ticker
        result = fetch_nifty50_history("^NSEI")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch("yfinance.Ticker")
    def test_fetch_called_with_correct_period(self, mock_ticker_cls):
        ticker = MagicMock()
        ticker.history.return_value = pd.DataFrame(
            columns=["Open", "High", "Low", "Close", "Volume"],
            index=pd.to_datetime([])
        )
        mock_ticker_cls.return_value = ticker
        fetch_nifty50_history("^NSEI", period="6mo")
        ticker.history.assert_called_once_with(period="6mo")
