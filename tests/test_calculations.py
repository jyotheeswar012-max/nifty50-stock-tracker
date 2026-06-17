"""Tests for utils/calculations.py."""
import math
import pytest
import pandas as pd
import numpy as np
from utils.calculations import (
    calculate_returns,
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
)


@pytest.fixture
def sample_prices():
    """A simple ascending price series."""
    return pd.Series([100.0, 102.0, 101.0, 105.0, 103.0, 108.0])


def test_calculate_returns_length(sample_prices):
    returns = calculate_returns(sample_prices)
    # pct_change drops the first NaN row
    assert len(returns.dropna()) == len(sample_prices) - 1


def test_calculate_returns_positive_trend(sample_prices):
    returns = calculate_returns(sample_prices)
    assert returns.dropna().mean() > 0


def test_calculate_volatility_non_negative(sample_prices):
    vol = calculate_volatility(sample_prices)
    assert vol >= 0


def test_calculate_volatility_constant_series():
    """Zero volatility for a flat price series."""
    flat = pd.Series([100.0] * 10)
    assert calculate_volatility(flat) == pytest.approx(0.0, abs=1e-9)


def test_calculate_sharpe_ratio_type(sample_prices):
    sr = calculate_sharpe_ratio(sample_prices)
    assert isinstance(sr, float)


def test_calculate_max_drawdown_non_positive(sample_prices):
    mdd = calculate_max_drawdown(sample_prices)
    assert mdd <= 0


def test_calculate_max_drawdown_flat():
    flat = pd.Series([50.0] * 5)
    assert calculate_max_drawdown(flat) == pytest.approx(0.0, abs=1e-9)
