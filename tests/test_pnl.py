"""Tests for P&L calculation logic."""
import pytest


def _pnl(buy_price: float, sell_price: float, qty: int) -> dict:
    """Inline P&L helper matching the app's logic."""
    invested = buy_price * qty
    current  = sell_price * qty
    gain     = current - invested
    pct      = (gain / invested * 100) if invested else 0.0
    return {"invested": invested, "current": current, "gain": gain, "pct": pct}


def test_profit_positive():
    r = _pnl(100, 120, 10)
    assert r["gain"] == pytest.approx(200.0)


def test_loss_negative():
    r = _pnl(200, 150, 5)
    assert r["gain"] == pytest.approx(-250.0)


def test_breakeven():
    r = _pnl(100, 100, 10)
    assert r["gain"] == pytest.approx(0.0)
    assert r["pct"]  == pytest.approx(0.0)


def test_percentage_gain():
    r = _pnl(100, 110, 1)
    assert r["pct"] == pytest.approx(10.0)


def test_percentage_loss():
    r = _pnl(100, 90, 1)
    assert r["pct"] == pytest.approx(-10.0)


def test_invested_amount():
    r = _pnl(250, 300, 4)
    assert r["invested"] == pytest.approx(1000.0)


def test_zero_quantity():
    r = _pnl(100, 200, 0)
    assert r["gain"] == pytest.approx(0.0)
