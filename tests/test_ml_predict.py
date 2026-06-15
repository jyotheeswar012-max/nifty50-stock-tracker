"""
tests/test_ml_predict.py
========================
Unit tests for utils/ml_predict.py

Run with:
    pytest tests/ -v
"""

import math
import pytest
import sys
import os

# Allow importing utils from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.ml_predict import calc_stock_impact, portfolio_scenario


# ── calc_stock_impact ──────────────────────────────────────────────────────────

class TestCalcStockImpact:

    def test_positive_nifty_move_beta_above_one(self):
        """Nifty +2%, beta 1.4 → stock +2.8%"""
        r = calc_stock_impact(nifty_pct=2.0, current_price=1000.0, quantity=10, beta=1.4)
        assert r["stock_pct"]    == pytest.approx(2.8,   rel=1e-4)
        assert r["price_change"] == pytest.approx(28.0,  rel=1e-4)
        assert r["new_price"]    == pytest.approx(1028.0,rel=1e-4)
        assert r["old_value"]    == pytest.approx(10000.0)
        assert r["new_value"]    == pytest.approx(10280.0)
        assert r["pnl_impact"]   == pytest.approx(280.0, rel=1e-4)

    def test_negative_nifty_move(self):
        """Nifty -3%, beta 1.0 → stock -3%"""
        r = calc_stock_impact(nifty_pct=-3.0, current_price=500.0, quantity=20, beta=1.0)
        assert r["stock_pct"]   == pytest.approx(-3.0)
        assert r["pnl_impact"]  == pytest.approx(-300.0)
        assert r["new_price"]   == pytest.approx(485.0)

    def test_defensive_stock_beta_below_one(self):
        """Beta 0.55 dampens market move."""
        r = calc_stock_impact(nifty_pct=4.0, current_price=2000.0, quantity=5, beta=0.55)
        assert r["stock_pct"]   == pytest.approx(2.2, rel=1e-4)
        assert r["price_change"]== pytest.approx(44.0, rel=1e-4)

    def test_zero_nifty_move(self):
        """No Nifty move → zero impact regardless of beta."""
        r = calc_stock_impact(nifty_pct=0.0, current_price=750.0, quantity=8, beta=1.5)
        assert r["stock_pct"]   == 0.0
        assert r["pnl_impact"]  == 0.0
        assert r["new_price"]   == pytest.approx(750.0)

    def test_negative_beta(self):
        """Inverse ETF / short instrument: beta -1.0"""
        r = calc_stock_impact(nifty_pct=5.0, current_price=100.0, quantity=100, beta=-1.0)
        assert r["stock_pct"]   == pytest.approx(-5.0)
        assert r["pnl_impact"]  == pytest.approx(-500.0)

    def test_large_quantity(self):
        """Scales correctly for large quantity."""
        r = calc_stock_impact(nifty_pct=1.0, current_price=3000.0, quantity=1000, beta=1.2)
        assert r["pnl_impact"]  == pytest.approx(36000.0, rel=1e-4)

    # ── Validation errors ───────────────────────────────────────────────────

    def test_invalid_price_zero(self):
        with pytest.raises(ValueError, match="current_price"):
            calc_stock_impact(2.0, 0.0, 10, 1.0)

    def test_invalid_price_negative(self):
        with pytest.raises(ValueError, match="current_price"):
            calc_stock_impact(2.0, -100.0, 10, 1.0)

    def test_invalid_quantity_zero(self):
        with pytest.raises(ValueError, match="quantity"):
            calc_stock_impact(2.0, 500.0, 0, 1.0)

    def test_invalid_quantity_negative(self):
        with pytest.raises(ValueError, match="quantity"):
            calc_stock_impact(2.0, 500.0, -5, 1.0)

    def test_invalid_beta_nan(self):
        with pytest.raises(ValueError, match="beta"):
            calc_stock_impact(2.0, 500.0, 10, math.nan)

    def test_invalid_beta_inf(self):
        with pytest.raises(ValueError, match="beta"):
            calc_stock_impact(2.0, 500.0, 10, math.inf)

    # ── Return type ─────────────────────────────────────────────────────────

    def test_return_keys(self):
        r = calc_stock_impact(1.0, 100.0, 1, 1.0)
        expected = {"stock_pct", "price_change", "new_price",
                    "old_value", "new_value", "pnl_impact"}
        assert set(r.keys()) == expected


# ── portfolio_scenario ─────────────────────────────────────────────────────────

class TestPortfolioScenario:

    HOLDINGS = [
        {"symbol": "RELIANCE",   "current_price": 2900.0, "quantity": 5,  "beta": 0.9},
        {"symbol": "TATAMOTORS", "current_price": 950.0,  "quantity": 20, "beta": 1.45},
    ]

    def test_positive_scenario_total_pnl_positive(self):
        out = portfolio_scenario(self.HOLDINGS, nifty_pct=2.0)
        assert out["total_pnl"] > 0
        assert out["total_pnl_pct"] > 0

    def test_negative_scenario_total_pnl_negative(self):
        out = portfolio_scenario(self.HOLDINGS, nifty_pct=-5.0)
        assert out["total_pnl"] < 0

    def test_zero_scenario(self):
        out = portfolio_scenario(self.HOLDINGS, nifty_pct=0.0)
        assert out["total_pnl"] == 0.0
        assert out["total_pnl_pct"] == 0.0

    def test_result_count_matches_holdings(self):
        out = portfolio_scenario(self.HOLDINGS, nifty_pct=1.0)
        assert len(out["results"]) == len(self.HOLDINGS)

    def test_symbol_preserved(self):
        out = portfolio_scenario(self.HOLDINGS, nifty_pct=1.0)
        symbols = [r["symbol"] for r in out["results"]]
        assert "RELIANCE" in symbols
        assert "TATAMOTORS" in symbols

    def test_total_old_value_correct(self):
        """total_old = sum(price * qty) for each holding."""
        out = portfolio_scenario(self.HOLDINGS, nifty_pct=1.0)
        expected = 2900.0 * 5 + 950.0 * 20
        assert out["total_old"] == pytest.approx(expected)

    def test_empty_holdings(self):
        out = portfolio_scenario([], nifty_pct=3.0)
        assert out["total_pnl"]  == 0.0
        assert out["results"]    == []
        assert out["total_pnl_pct"] == 0.0

    def test_single_holding_matches_individual(self):
        """portfolio_scenario with one stock must match calc_stock_impact."""
        h = [{"symbol": "TCS", "current_price": 3500.0, "quantity": 10, "beta": 0.7}]
        out  = portfolio_scenario(h, nifty_pct=2.0)
        single = calc_stock_impact(2.0, 3500.0, 10, 0.7)
        assert out["total_pnl"]  == pytest.approx(single["pnl_impact"])
        assert out["total_old"]  == pytest.approx(single["old_value"])
        assert out["total_new"]  == pytest.approx(single["new_value"])
