"""Focused P&L and beta-impact edge-case tests."""
from __future__ import annotations

import pytest
from utils.calculations import calc_pl, calc_beta_impact


class TestPLEdgeCases:
    """Edge-cases and boundary conditions for calc_pl."""

    def test_buy_equals_sell_zero_pl(self):
        pl, _, _ = calc_pl(100.0, 100.0, 50)
        assert pl == pytest.approx(0.0)

    def test_single_share_profit(self):
        pl, inv, ret = calc_pl(1000.0, 1100.0, 1)
        assert pl  == pytest.approx(100.0)
        assert inv == pytest.approx(1000.0)
        assert ret == pytest.approx(10.0)

    def test_very_small_prices(self):
        pl, inv, ret = calc_pl(0.01, 0.02, 1000)
        assert pl  == pytest.approx(10.0)
        assert ret == pytest.approx(100.0)

    def test_very_large_prices(self):
        pl, inv, ret = calc_pl(100_000.0, 110_000.0, 100)
        assert pl  == pytest.approx(1_000_000.0)
        assert ret == pytest.approx(10.0)

    def test_negative_effective_return_is_negative(self):
        _, _, ret = calc_pl(500.0, 400.0, 10)
        assert ret < 0

    def test_investment_always_positive_for_positive_buy(self):
        _, inv, _ = calc_pl(250.0, 300.0, 5)
        assert inv > 0

    def test_return_calculation_precision(self):
        pl, inv, ret = calc_pl(333.33, 400.0, 3)
        expected_ret = (400.0 - 333.33) / 333.33 * 100
        assert ret == pytest.approx(expected_ret, rel=1e-4)

    @pytest.mark.parametrize("buy, sell, qty", [
        (100.0, 150.0, 10),
        (500.0, 600.0,  1),
        (200.0, 250.0, 25),
        (1000.0, 900.0, 5),
    ])
    def test_parametrized_pl_sign(self, buy, sell, qty):
        pl, _, _ = calc_pl(buy, sell, qty)
        if sell > buy:
            assert pl > 0
        elif sell < buy:
            assert pl < 0
        else:
            assert pl == pytest.approx(0.0)


class TestBetaImpactEdgeCases:
    """Edge-cases and boundary conditions for calc_beta_impact."""

    def test_symmetry_positive_negative_nifty(self):
        """P&L from +5% and -5% Nifty move should cancel out."""
        _, _, _, _, _, pl_up   = calc_beta_impact( 5.0, 1000.0, 10, 1.0)
        _, _, _, _, _, pl_down = calc_beta_impact(-5.0, 1000.0, 10, 1.0)
        assert pl_up == pytest.approx(-pl_down)

    def test_high_beta_amplifies_more_than_low_beta(self):
        _, _, _, _, _, pl_high = calc_beta_impact(10.0, 1000.0, 1, 2.0)
        _, _, _, _, _, pl_low  = calc_beta_impact(10.0, 1000.0, 1, 0.5)
        assert pl_high > pl_low

    def test_more_shares_amplify_pl_linearly(self):
        _, _, _, _, _, pl1 = calc_beta_impact(5.0, 1000.0, 1,  1.0)
        _, _, _, _, _, pl2 = calc_beta_impact(5.0, 1000.0, 10, 1.0)
        assert pl2 == pytest.approx(pl1 * 10)

    def test_old_value_equals_price_times_qty(self):
        _, _, _, ov, _, _ = calc_beta_impact(5.0, 500.0, 20, 1.0)
        assert ov == pytest.approx(500.0 * 20)

    @pytest.mark.parametrize("nifty_pct,beta", [
        (1.0, 1.0), (5.0, 1.5), (-3.0, 0.8), (0.0, 2.0), (10.0, 0.0),
    ])
    def test_parametrized_stock_pct_equals_nifty_times_beta(self, nifty_pct, beta):
        spct, *_ = calc_beta_impact(nifty_pct, 1000.0, 1, beta)
        assert spct == pytest.approx(nifty_pct * beta)
