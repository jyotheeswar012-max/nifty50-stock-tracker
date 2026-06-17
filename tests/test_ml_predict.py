"""Tests for utils/ml_predict.py."""
import pytest
import numpy as np
import pandas as pd


def _make_price_series(n=60, start=100.0, drift=0.001):
    """Synthetic daily close prices for ML tests."""
    rng   = np.random.default_rng(42)
    noise = rng.normal(0, 1, n)
    prices = [start]
    for r in noise:
        prices.append(prices[-1] * (1 + drift + r * 0.01))
    return pd.Series(prices[:n])


def test_price_series_length():
    s = _make_price_series(60)
    assert len(s) == 60


def test_price_series_positive():
    s = _make_price_series()
    assert (s > 0).all()


def test_ml_predict_importable():
    """Check the module loads without crashing."""
    import importlib
    mod = importlib.import_module("utils.ml_predict")
    assert mod is not None


def test_moving_average_shape():
    """Simple MA calculation used inside ml_predict."""
    s = _make_price_series(60)
    ma20 = s.rolling(20).mean()
    assert len(ma20) == 60
    assert ma20.iloc[:19].isna().all()
    assert not pd.isna(ma20.iloc[19])
