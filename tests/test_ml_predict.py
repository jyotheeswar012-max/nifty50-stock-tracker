"""Tests for utils/ml_predict.py."""
import importlib
import pytest
import numpy as np
import pandas as pd


def _make_price_series(n=60, start=100.0, drift=0.001):
    rng    = np.random.default_rng(42)
    noise  = rng.normal(0, 1, n)
    prices = [start]
    for r in noise:
        prices.append(prices[-1] * (1 + drift + r * 0.01))
    return pd.Series(prices[:n])


def test_price_series_length():
    assert len(_make_price_series(60)) == 60


def test_price_series_positive():
    assert (_make_price_series() > 0).all()


def test_ml_predict_importable():
    mod = importlib.import_module("utils.ml_predict")
    assert mod is not None


def test_moving_average_shape():
    s    = _make_price_series(60)
    ma20 = s.rolling(20).mean()
    assert len(ma20) == 60
    assert ma20.iloc[:19].isna().all()
    assert not pd.isna(ma20.iloc[19])


def test_pct_change_no_nan_after_first():
    s    = _make_price_series(30)
    pct  = s.pct_change().dropna()
    assert len(pct) == 29
    assert not pct.isna().any()
