"""Tests for P&L helpers (delegates to calc_pl in calculations.py)."""
import pytest
from utils.calculations import calc_pl


def test_profit_positive():
    pl, _, _ = calc_pl(100, 120, 10)
    assert pl == pytest.approx(200.0)


def test_loss_negative():
    pl, _, _ = calc_pl(200, 150, 5)
    assert pl == pytest.approx(-250.0)


def test_breakeven():
    pl, _, ret = calc_pl(100, 100, 10)
    assert pl  == pytest.approx(0.0)
    assert ret == pytest.approx(0.0)


def test_percentage_gain():
    _, _, ret = calc_pl(100, 110, 1)
    assert ret == pytest.approx(10.0)


def test_percentage_loss():
    _, _, ret = calc_pl(100, 90, 1)
    assert ret == pytest.approx(-10.0)


def test_invested_amount():
    _, inv, _ = calc_pl(250, 300, 4)
    assert inv == pytest.approx(1000.0)


def test_zero_quantity():
    pl, inv, ret = calc_pl(100, 200, 0)
    assert pl  == pytest.approx(0.0)
    assert inv == pytest.approx(0.0)
