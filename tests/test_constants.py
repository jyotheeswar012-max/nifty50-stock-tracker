"""Deep validation of constants.py — sector coverage, beta ranges, FAMOUS_DATES."""
from __future__ import annotations

from datetime import date
import pytest

from utils.constants import NIFTY50, NSE_INDICES, SYMBOLS, FAMOUS_DATES


KNOWN_SECTORS = {
    "Energy", "Financial Services", "IT", "Telecom", "FMCG",
    "Construction", "Automobile", "Metals", "Conglomerate",
    "Infrastructure", "Pharma", "Consumer Goods", "Cement",
    "Power", "Defence",
}


class TestNifty50Sectors:
    def test_all_sectors_are_known(self):
        for s in NIFTY50:
            assert s["sector"] in KNOWN_SECTORS, (
                f"{s['name']} has unknown sector '{s['sector']}'"
            )

    def test_sector_coverage_has_it(self):
        sectors = {s["sector"] for s in NIFTY50}
        assert "IT" in sectors

    def test_sector_coverage_has_financial(self):
        sectors = {s["sector"] for s in NIFTY50}
        assert "Financial Services" in sectors

    def test_sector_coverage_has_energy(self):
        sectors = {s["sector"] for s in NIFTY50}
        assert "Energy" in sectors


class TestBetaRanges:
    def test_all_betas_in_reasonable_range(self):
        """Real-world Nifty 50 betas are roughly 0.5 – 1.7."""
        for s in NIFTY50:
            assert 0.3 <= s["beta"] <= 2.0, (
                f"{s['name']} beta={s['beta']} seems unrealistic"
            )

    def test_defensive_stocks_have_low_beta(self):
        """FMCG & Pharma betas should be < 1 (defensive)."""
        for s in NIFTY50:
            if s["sector"] in ("FMCG", "Pharma"):
                assert s["beta"] < 1.1, (
                    f"{s['name']} ({s['sector']}) beta={s['beta']} expected < 1.1"
                )

    def test_high_volatility_stocks_have_higher_beta(self):
        """Metals betas should be >= 1.2 (cyclical)."""
        for s in NIFTY50:
            if s["sector"] == "Metals":
                assert s["beta"] >= 1.2, (
                    f"{s['name']} (Metals) beta={s['beta']} expected >= 1.2"
                )


class TestFamousDates:
    def test_all_dates_in_past(self):
        today = date.today()
        for label, d in FAMOUS_DATES.items():
            assert d <= today, f"{label}: {d} is in the future"

    def test_all_dates_after_2000(self):
        for label, d in FAMOUS_DATES.items():
            assert d.year >= 2000, f"{label}: year {d.year} seems wrong"

    def test_covid_crash_is_march_2020(self):
        covid_key = next((k for k in FAMOUS_DATES if "COVID" in k and "Crash" in k), None)
        assert covid_key is not None
        d = FAMOUS_DATES[covid_key]
        assert d.year == 2020
        assert d.month == 3

    def test_no_duplicate_dates(self):
        dates = list(FAMOUS_DATES.values())
        assert len(dates) == len(set(dates)), "Duplicate dates found in FAMOUS_DATES"


class TestSymbolsList:
    def test_symbols_is_list_of_strings(self):
        assert isinstance(SYMBOLS, list)
        assert all(isinstance(s, str) for s in SYMBOLS)

    def test_symbols_length_equals_nifty50(self):
        assert len(SYMBOLS) == len(NIFTY50)

    def test_reliance_in_symbols(self):
        assert "RELIANCE.NS" in SYMBOLS

    def test_tcs_in_symbols(self):
        assert "TCS.NS" in SYMBOLS

    def test_infy_in_symbols(self):
        assert "INFY.NS" in SYMBOLS


class TestNseIndicesDetail:
    def test_nifty_bank_present(self):
        symbols = [i["symbol"] for i in NSE_INDICES]
        assert "^NSEBANK" in symbols

    def test_nifty_it_present(self):
        symbols = [i["symbol"] for i in NSE_INDICES]
        assert "^CNXIT" in symbols

    def test_all_names_non_empty(self):
        for idx in NSE_INDICES:
            assert len(idx["name"]) > 0

    def test_all_colors_valid_hex(self):
        import re
        hex_re = re.compile(r'^#[0-9a-fA-F]{6}$')
        for idx in NSE_INDICES:
            assert hex_re.match(idx["color"]), (
                f"{idx['name']} color '{idx['color']}' is not a valid 6-digit hex"
            )
