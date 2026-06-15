"""Smoke-tests for utils/constants.py

Verifies structural integrity of all static data — catches accidental
duplicate symbols, missing fields, and malformed values before they
hit production.
"""
import pytest
from utils.constants import (
    NIFTY50, SYMBOLS, NSE_INDICES, FAMOUS_DATES,
    PLT_LAYOUT, AXIS_STYLE, REFRESH_MS, CACHE_TTL,
)


class TestNifty50List:
    def test_has_50_stocks(self):
        assert len(NIFTY50) == 50

    def test_required_keys_present(self):
        required = {"symbol", "name", "sector", "beta"}
        for stock in NIFTY50:
            assert required.issubset(stock.keys()), f"Missing keys in {stock}"

    def test_no_duplicate_symbols(self):
        syms = [s["symbol"] for s in NIFTY50]
        assert len(syms) == len(set(syms)), "Duplicate symbols found"

    def test_all_symbols_end_with_ns(self):
        for s in NIFTY50:
            assert s["symbol"].endswith(".NS"), f"{s['symbol']} missing .NS suffix"

    def test_beta_is_positive_float(self):
        for s in NIFTY50:
            assert isinstance(s["beta"], (int, float)), f"{s['symbol']} beta not numeric"
            assert s["beta"] > 0, f"{s['symbol']} beta must be positive"

    def test_sector_is_non_empty_string(self):
        for s in NIFTY50:
            assert isinstance(s["sector"], str) and s["sector"], \
                f"{s['symbol']} has empty sector"


class TestSymbolsList:
    def test_symbols_matches_nifty50(self):
        expected = [s["symbol"] for s in NIFTY50]
        assert SYMBOLS == expected

    def test_length(self):
        assert len(SYMBOLS) == 50


class TestNseIndices:
    def test_has_8_indices(self):
        assert len(NSE_INDICES) == 8

    def test_required_keys(self):
        for idx in NSE_INDICES:
            assert {"symbol", "name", "color"}.issubset(idx.keys())

    def test_color_is_hex(self):
        import re
        hex_re = re.compile(r"^#[0-9a-fA-F]{6}$")
        for idx in NSE_INDICES:
            assert hex_re.match(idx["color"]), \
                f"{idx['name']} color '{idx['color']}' is not a valid 6-digit hex"


class TestFamousDates:
    def test_non_empty(self):
        assert len(FAMOUS_DATES) > 0

    def test_values_are_dates(self):
        from datetime import date
        for label, d in FAMOUS_DATES.items():
            assert isinstance(d, date), f"'{label}' value is not a date"


class TestPlotlyConfig:
    def test_plt_layout_is_dict(self):
        assert isinstance(PLT_LAYOUT, dict)

    def test_plt_layout_has_expected_keys(self):
        assert "paper_bgcolor" in PLT_LAYOUT
        assert "plot_bgcolor"  in PLT_LAYOUT
        assert "margin"        in PLT_LAYOUT

    def test_axis_style_is_dict(self):
        assert isinstance(AXIS_STYLE, dict)


class TestCacheConstants:
    def test_refresh_ms_positive(self):
        assert REFRESH_MS > 0

    def test_cache_ttl_positive(self):
        assert CACHE_TTL > 0
