"""Unit tests for data cleaning & utility functions."""
import pytest
import pandas as pd
import numpy as np


# ── helpers (inline stand-ins so tests run without the full app) ──────────────
# In your real project these would be: from utils import clean_ohlcv, calc_returns, ...

def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with any NaN, ensure DatetimeIndex, sort ascending."""
    df = df.copy()
    if "Date" in df.columns:
        df = df.set_index("Date")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index().dropna()
    return df


def calc_daily_returns(df: pd.DataFrame, col: str = "Close") -> pd.Series:
    return df[col].pct_change().dropna()


def calc_cumulative_returns(returns: pd.Series) -> pd.Series:
    return (1 + returns).cumprod() - 1


def calc_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.06) -> float:
    excess = returns - risk_free_rate / 252
    if excess.std() == 0:
        return 0.0
    return float((excess.mean() / excess.std()) * np.sqrt(252))


def calc_max_drawdown(prices: pd.Series) -> float:
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    return float(drawdown.min())


def add_moving_averages(df: pd.DataFrame, windows=(20, 50, 200)) -> pd.DataFrame:
    df = df.copy()
    for w in windows:
        df[f"MA{w}"] = df["Close"].rolling(w).mean()
    return df


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCleanOHLCV:
    def test_sets_datetime_index(self, raw_price_data):
        result = clean_ohlcv(raw_price_data)
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_drops_nan_rows(self, raw_price_data):
        dirty = raw_price_data.copy()
        dirty.loc[0, "Close"] = np.nan
        result = clean_ohlcv(dirty)
        assert result.isna().sum().sum() == 0

    def test_sorted_ascending(self, raw_price_data):
        shuffled = raw_price_data.sample(frac=1, random_state=7).reset_index(drop=True)
        result = clean_ohlcv(shuffled)
        assert result.index.is_monotonic_increasing

    def test_no_empty_dataframe(self, raw_price_data):
        result = clean_ohlcv(raw_price_data)
        assert not result.empty

    def test_expected_columns_present(self, raw_price_data):
        result = clean_ohlcv(raw_price_data)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in result.columns


class TestCalcDailyReturns:
    def test_length_is_n_minus_1(self, cleaned_price_data):
        returns = calc_daily_returns(cleaned_price_data)
        assert len(returns) == len(cleaned_price_data) - 1

    def test_returns_are_floats(self, cleaned_price_data):
        returns = calc_daily_returns(cleaned_price_data)
        assert returns.dtype == float

    def test_no_nan_in_output(self, cleaned_price_data):
        returns = calc_daily_returns(cleaned_price_data)
        assert returns.isna().sum() == 0

    def test_returns_reasonable_magnitude(self, cleaned_price_data):
        returns = calc_daily_returns(cleaned_price_data)
        assert returns.abs().max() < 0.20, "Daily return > 20% seems wrong for Nifty 50"


class TestCumulativeReturns:
    def test_starts_near_zero(self, cleaned_price_data):
        ret = calc_daily_returns(cleaned_price_data)
        cum = calc_cumulative_returns(ret)
        assert abs(cum.iloc[0]) < 0.05

    def test_length_matches_daily_returns(self, cleaned_price_data):
        ret = calc_daily_returns(cleaned_price_data)
        cum = calc_cumulative_returns(ret)
        assert len(cum) == len(ret)

    def test_monotone_if_all_positive(self):
        returns = pd.Series([0.01] * 10)
        cum = calc_cumulative_returns(returns)
        assert cum.is_monotonic_increasing


class TestSharpeRatio:
    def test_positive_for_positive_mean_return(self, cleaned_price_data):
        ret = calc_daily_returns(cleaned_price_data)
        if ret.mean() > 0:
            assert calc_sharpe_ratio(ret) > 0

    def test_returns_float(self, cleaned_price_data):
        ret = calc_daily_returns(cleaned_price_data)
        assert isinstance(calc_sharpe_ratio(ret), float)

    def test_zero_std_returns_zero(self):
        flat_returns = pd.Series([0.0] * 20)
        assert calc_sharpe_ratio(flat_returns) == 0.0

    def test_custom_risk_free_rate(self, cleaned_price_data):
        ret = calc_daily_returns(cleaned_price_data)
        s1 = calc_sharpe_ratio(ret, risk_free_rate=0.04)
        s2 = calc_sharpe_ratio(ret, risk_free_rate=0.08)
        assert s1 != s2


class TestMaxDrawdown:
    def test_drawdown_is_negative_or_zero(self, cleaned_price_data):
        dd = calc_max_drawdown(cleaned_price_data["Close"])
        assert dd <= 0

    def test_flat_series_has_zero_drawdown(self):
        flat = pd.Series([100.0] * 20)
        assert calc_max_drawdown(flat) == 0.0

    def test_declining_series_has_negative_drawdown(self):
        declining = pd.Series([100, 95, 90, 85, 80])
        assert calc_max_drawdown(declining) < 0


class TestMovingAverages:
    def test_ma_columns_added(self, cleaned_price_data):
        result = add_moving_averages(cleaned_price_data)
        for col in ["MA20", "MA50", "MA200"]:
            assert col in result.columns

    def test_ma20_has_nan_for_first_19_rows(self, cleaned_price_data):
        result = add_moving_averages(cleaned_price_data)
        assert result["MA20"].iloc[:19].isna().all()

    def test_does_not_mutate_input(self, cleaned_price_data):
        original_cols = set(cleaned_price_data.columns)
        add_moving_averages(cleaned_price_data)
        assert set(cleaned_price_data.columns) == original_cols
