"""Tests for utils/constants.py."""
import pytest
from utils.constants import NIFTY50_SYMBOLS, NIFTY50


def test_nifty50_has_50_entries():
    assert len(NIFTY50) == 50, f"Expected 50 stocks, got {len(NIFTY50)}"


def test_nifty50_symbols_not_empty():
    assert len(NIFTY50_SYMBOLS) > 0


def test_all_symbols_end_with_ns():
    for sym in NIFTY50_SYMBOLS:
        assert sym.endswith(".NS"), f"{sym} does not end with .NS"


def test_nifty50_entries_have_required_keys():
    for entry in NIFTY50:
        assert "symbol" in entry, f"Missing 'symbol' in {entry}"
        assert "name" in entry, f"Missing 'name' in {entry}"


def test_nifty50_symbols_are_unique():
    assert len(NIFTY50_SYMBOLS) == len(set(NIFTY50_SYMBOLS)), "Duplicate symbols found"


def test_reliance_present():
    assert "RELIANCE.NS" in NIFTY50_SYMBOLS


def test_tcs_present():
    assert "TCS.NS" in NIFTY50_SYMBOLS
