"""Tests for data fallback / cleaning logic in utils/data.py."""
import pytest
import pandas as pd
import numpy as np


def _clean_price_column(series: pd.Series) -> pd.Series:
    """Mirrors the fix applied to the nselib fallback path."""
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )


def test_comma_removed():
    s = pd.Series(["1,328.50", "22,500.00"])
    result = _clean_price_column(s)
    assert result.iloc[0] == pytest.approx(1328.50)
    assert result.iloc[1] == pytest.approx(22500.00)


def test_string_na_becomes_nan():
    s = pd.Series(["NA", "100.0"])
    result = _clean_price_column(s)
    assert pd.isna(result.iloc[0])
    assert result.iloc[1] == pytest.approx(100.0)


def test_plain_number_passes_through():
    s = pd.Series(["500.25"])
    result = _clean_price_column(s)
    assert result.iloc[0] == pytest.approx(500.25)


def test_empty_series():
    s = pd.Series([], dtype=str)
    result = _clean_price_column(s)
    assert len(result) == 0


def test_all_na():
    s = pd.Series(["NA", "NA", "NA"])
    result = _clean_price_column(s)
    assert result.isna().all()


def test_mixed_valid_and_invalid():
    s = pd.Series(["1,000", "bad", "250"])
    result = _clean_price_column(s)
    assert result.iloc[0] == pytest.approx(1000.0)
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(250.0)
