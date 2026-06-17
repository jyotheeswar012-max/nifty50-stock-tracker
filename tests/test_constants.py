"""Tests for utils/constants.py."""
import pytest
from utils.constants import SYMBOLS, NIFTY50


def test_nifty50_has_50_entries():
    assert len(NIFTY50) == 50, f"Expected 50 stocks, got {len(NIFTY50)}"


def test_symbols_not_empty():
    assert len(SYMBOLS) > 0


def test_all_symbols_end_with_ns():
    for sym in SYMBOLS:
        assert sym.endswith(".NS"), f"{sym} does not end with .NS"


def test_nifty50_entries_have_required_keys():
    for entry in NIFTY50:
        assert "symbol" in entry, f"Missing 'symbol' in {entry}"
        assert "name"   in entry, f"Missing 'name' in {entry}"
        assert "sector" in entry, f"Missing 'sector' in {entry}"
        assert "beta"   in entry, f"Missing 'beta' in {entry}"


def test_symbols_are_unique():
    assert len(SYMBOLS) == len(set(SYMBOLS)), "Duplicate symbols found"


def test_symbols_matches_nifty50():
    derived = [s["symbol"] for s in NIFTY50]
    assert SYMBOLS == derived


def test_reliance_present():
    assert "RELIANCE.NS" in SYMBOLS


def test_tcs_present():
    assert "TCS.NS" in SYMBOLS


def test_beta_values_are_numeric():
    for entry in NIFTY50:
        assert isinstance(entry["beta"], (int, float)), f"Non-numeric beta in {entry['symbol']}"
        assert entry["beta"] > 0, f"Non-positive beta in {entry['symbol']}"
