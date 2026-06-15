"""
utils/ml_predict.py
===================
Beta-Weighted Linear Impact Model for the NSE Scenario Engine.

Methodology
-----------
This module implements a CAPM-style (Capital Asset Pricing Model) linear
approximation to estimate how individual Nifty 50 stocks respond to a
market-wide percentage move (e.g. triggered by a macro event).

Formula
-------
    stock_pct_change  = nifty_pct_change * beta
    price_change      = current_price * (stock_pct_change / 100)
    new_price         = current_price + price_change
    pnl_impact        = price_change * quantity

Assumptions
-----------
1. Linear relationship between index and stock returns (single-factor CAPM).
2. Beta values are static and pre-computed from historical data.
   They do NOT update in real-time.
3. No transaction costs, slippage, or liquidity constraints.
4. No non-linear effects (earnings surprises, circuit breakers, etc.).
5. Short time horizon (intraday / single session estimate only).

Limitations
-----------
- Beta drift: a stock's beta changes over time; static betas may be stale.
- Regime breaks: during extreme volatility, correlations collapse and
  beta loses predictive power.
- No sector rotation or stock-specific news is modelled.

Data Source Note
----------------
Currently uses yfinance (Yahoo Finance) via yf.Ticker.history().
For production-level reliability, consider:
  - NSE official data API (https://www.nseindia.com/api/)
  - nsetools (https://nsetools.readthedocs.io/) for live quotes
  - Zerodha Kite Connect API for authenticated real-time feeds
"""

from __future__ import annotations
import math


def calc_stock_impact(
    nifty_pct: float,
    current_price: float,
    quantity: int,
    beta: float,
) -> dict:
    """
    Estimate the P&L impact on a single stock holding given a Nifty % move.

    Parameters
    ----------
    nifty_pct : float
        Expected percentage change in Nifty 50 (e.g. -3.5 means a 3.5% drop).
    current_price : float
        Last traded / closing price of the stock in INR.
    quantity : int
        Number of shares held.
    beta : float
        Stock's beta coefficient relative to Nifty 50.
        beta > 1  → stock amplifies market moves
        beta < 1  → stock is defensive / less volatile
        beta = 1  → moves in line with the index

    Returns
    -------
    dict with keys:
        stock_pct   : float  – estimated % change for the stock
        price_change: float  – INR change per share
        new_price   : float  – estimated new price
        old_value   : float  – portfolio value before the move
        new_value   : float  – portfolio value after the move
        pnl_impact  : float  – net P&L in INR (positive = gain)

    Raises
    ------
    ValueError if current_price <= 0, quantity <= 0, or beta is not finite.

    Examples
    --------
    >>> result = calc_stock_impact(-3.0, 1500.0, 10, 1.4)
    >>> round(result["stock_pct"], 2)
    -4.2
    >>> round(result["pnl_impact"], 2)
    -630.0
    """
    if current_price <= 0:
        raise ValueError(f"current_price must be > 0, got {current_price}")
    if quantity <= 0:
        raise ValueError(f"quantity must be > 0, got {quantity}")
    if not math.isfinite(beta):
        raise ValueError(f"beta must be a finite number, got {beta}")

    stock_pct    = nifty_pct * beta
    price_change = current_price * (stock_pct / 100)
    new_price    = current_price + price_change
    old_value    = current_price * quantity
    new_value    = new_price * quantity
    pnl_impact   = price_change * quantity

    return {
        "stock_pct":    round(stock_pct,    4),
        "price_change": round(price_change, 4),
        "new_price":    round(new_price,    4),
        "old_value":    round(old_value,    4),
        "new_value":    round(new_value,    4),
        "pnl_impact":   round(pnl_impact,   4),
    }


def portfolio_scenario(
    holdings: list[dict],
    nifty_pct: float,
) -> dict:
    """
    Run a scenario across a multi-stock portfolio.

    Parameters
    ----------
    holdings : list of dicts, each with keys:
        symbol        : str
        current_price : float
        quantity      : int
        beta          : float
    nifty_pct : float
        Expected Nifty % change for the scenario.

    Returns
    -------
    dict with keys:
        results      : list of per-stock impact dicts (same as calc_stock_impact)
        total_old    : float  – total portfolio value before
        total_new    : float  – total portfolio value after
        total_pnl    : float  – net portfolio P&L in INR
        total_pnl_pct: float  – net portfolio % change

    Examples
    --------
    >>> h = [
    ...     {"symbol": "RELIANCE", "current_price": 2900.0, "quantity": 5,  "beta": 0.9},
    ...     {"symbol": "TATAMOTORS","current_price": 950.0,  "quantity": 20, "beta": 1.45},
    ... ]
    >>> out = portfolio_scenario(h, nifty_pct=2.0)
    >>> out["total_pnl"] > 0
    True
    """
    results   = []
    total_old = 0.0
    total_new = 0.0

    for h in holdings:
        r = calc_stock_impact(
            nifty_pct=nifty_pct,
            current_price=h["current_price"],
            quantity=h["quantity"],
            beta=h["beta"],
        )
        r["symbol"] = h.get("symbol", "?")
        results.append(r)
        total_old += r["old_value"]
        total_new += r["new_value"]

    total_pnl     = round(total_new - total_old, 4)
    total_pnl_pct = round((total_pnl / total_old * 100) if total_old else 0.0, 4)

    return {
        "results":       results,
        "total_old":     round(total_old, 4),
        "total_new":     round(total_new, 4),
        "total_pnl":     total_pnl,
        "total_pnl_pct": total_pnl_pct,
    }
