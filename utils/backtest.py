"""
utils/backtest.py  —  Vectorised strategy back-tester for Paper Portfolio.

Supported strategies
--------------------
  sma_cross   — dual SMA crossover  (fast / slow window)
  ema_cross   — dual EMA crossover  (fast / slow window)
  rsi         — RSI mean-reversion  (oversold / overbought thresholds)
  macd        — MACD signal-line cross

All strategies return a BacktestResult dataclass with:
  - equity curve (pd.Series indexed by date)
  - per-trade log (pd.DataFrame)
  - summary metrics dict: CAGR, Sharpe, max_drawdown, Calmar, win_rate,
    total_trades, avg_hold_days

Design notes
------------
* Pure NumPy / Pandas — no yfinance calls here; caller passes OHLCV df.
* All arithmetic uses log-returns to avoid compounding bias.
* Slippage model: 0.05 % per side (configurable via SlippageModel).
* No look-ahead bias: signals are shifted by 1 bar before position sizing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from utils.logger import get_logger

log = get_logger(__name__)

StrategyName = Literal["sma_cross", "ema_cross", "rsi", "macd"]

DEFAULT_SLIPPAGE = 0.0005   # 0.05 % per side
DEFAULT_CAPITAL  = 100_000  # INR


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    symbol:        str
    strategy:      str
    params:        dict
    equity_curve:  pd.Series          # date -> portfolio value
    drawdown:      pd.Series          # date -> drawdown fraction
    trade_log:     pd.DataFrame       # one row per completed round-trip
    metrics:       dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metrics:
            self.metrics = _calc_metrics(
                self.equity_curve, self.trade_log
            )


# ---------------------------------------------------------------------------
# Technical indicator helpers (private)
# ---------------------------------------------------------------------------

def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(com=period - 1, adjust=False).mean()
    avg_l = loss.ewm(com=period - 1, adjust=False).mean()
    rs    = avg_g / avg_l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd_line(close: pd.Series, fast: int = 12, slow: int = 26) -> tuple[pd.Series, pd.Series]:
    macd   = _ema(close, fast) - _ema(close, slow)
    signal = _ema(macd, 9)
    return macd, signal


# ---------------------------------------------------------------------------
# Signal generators (return +1 long / 0 flat / -1 short series)
# ---------------------------------------------------------------------------

def _signals_sma_cross(close: pd.Series, fast: int, slow: int) -> pd.Series:
    f = _sma(close, fast)
    s = _sma(close, slow)
    raw = np.where(f > s, 1, 0)
    return pd.Series(raw, index=close.index, dtype=int)


def _signals_ema_cross(close: pd.Series, fast: int, slow: int) -> pd.Series:
    f = _ema(close, fast)
    s = _ema(close, slow)
    raw = np.where(f > s, 1, 0)
    return pd.Series(raw, index=close.index, dtype=int)


def _signals_rsi(
    close: pd.Series,
    period: int,
    oversold: float,
    overbought: float,
) -> pd.Series:
    r   = _rsi(close, period)
    pos = pd.Series(0, index=close.index, dtype=int)
    pos[r < oversold]   = 1
    pos[r > overbought] = 0
    # forward-fill so position is held until opposite threshold
    pos = pos.replace(0, np.nan).ffill().fillna(0).astype(int)
    return pos


def _signals_macd(close: pd.Series, fast: int, slow: int) -> pd.Series:
    macd, signal = _macd_line(close, fast, slow)
    raw = np.where(macd > signal, 1, 0)
    return pd.Series(raw, index=close.index, dtype=int)


# ---------------------------------------------------------------------------
# Core simulation engine
# ---------------------------------------------------------------------------

def _simulate(
    close: pd.Series,
    signals: pd.Series,
    initial_capital: float,
    slippage: float,
) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """
    Simulate a long-only strategy given a binary signal series.

    Returns
    -------
    equity_curve : pd.Series
    drawdown     : pd.Series
    trade_log    : pd.DataFrame
    """
    # Shift by 1 to avoid look-ahead: trade on the *next* bar's open
    pos = signals.shift(1).fillna(0).astype(int)

    # Daily log-returns of the close price
    log_ret = np.log(close / close.shift(1)).fillna(0)

    # Strategy returns = position * (log_ret - slippage on entry/exit)
    trade_cost = slippage * pos.diff().abs().fillna(0)
    strat_ret  = pos * log_ret - trade_cost

    # Equity curve
    equity = initial_capital * np.exp(strat_ret.cumsum())
    equity = pd.Series(equity.values, index=close.index)

    # Drawdown
    rolling_max = equity.cummax()
    drawdown    = (equity - rolling_max) / rolling_max

    # Build trade log (entry / exit on position changes)
    changes   = pos.diff().fillna(0)
    entries   = close[changes == 1].index
    exits     = close[changes == -1].index

    trades: list[dict] = []
    for entry_dt in entries:
        # Find the next exit after this entry
        future_exits = exits[exits > entry_dt]
        if len(future_exits) == 0:
            exit_dt    = close.index[-1]
            exit_price = close.iloc[-1]
        else:
            exit_dt    = future_exits[0]
            exit_price = close[exit_dt]
        entry_price = close[entry_dt]
        pnl_pct     = (exit_price - entry_price) / entry_price * 100
        hold_days   = (exit_dt - entry_dt).days
        trades.append({
            "entry_date":  entry_dt,
            "exit_date":   exit_dt,
            "entry_price": round(entry_price, 2),
            "exit_price":  round(exit_price, 2),
            "pnl_pct":     round(pnl_pct, 3),
            "hold_days":   hold_days,
            "result":      "win" if pnl_pct > 0 else "loss",
        })

    trade_log = pd.DataFrame(trades)
    return equity, drawdown, trade_log


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _calc_metrics(equity: pd.Series, trade_log: pd.DataFrame) -> dict:
    if equity.empty or len(equity) < 2:
        return {}

    years       = (equity.index[-1] - equity.index[0]).days / 365.25
    total_ret   = (equity.iloc[-1] / equity.iloc[0]) - 1
    cagr        = (1 + total_ret) ** (1 / max(years, 0.01)) - 1

    daily_ret   = equity.pct_change().dropna()
    sharpe      = (
        daily_ret.mean() / daily_ret.std() * np.sqrt(252)
        if daily_ret.std() > 0 else 0.0
    )

    rolling_max = equity.cummax()
    drawdown    = (equity - rolling_max) / rolling_max
    max_dd      = drawdown.min()
    calmar      = cagr / abs(max_dd) if max_dd != 0 else 0.0

    if trade_log.empty:
        win_rate     = 0.0
        total_trades = 0
        avg_hold     = 0.0
    else:
        total_trades = len(trade_log)
        win_rate     = (trade_log["result"] == "win").mean() * 100
        avg_hold     = trade_log["hold_days"].mean()

    return {
        "cagr":          round(cagr * 100, 2),
        "sharpe":        round(sharpe, 3),
        "max_drawdown":  round(max_dd * 100, 2),
        "calmar":        round(calmar, 3),
        "win_rate":      round(win_rate, 1),
        "total_trades":  total_trades,
        "avg_hold_days": round(avg_hold, 1),
        "total_return":  round(total_ret * 100, 2),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_backtest(
    symbol: str,
    close: pd.Series,
    strategy: StrategyName = "sma_cross",
    params: dict | None = None,
    initial_capital: float = DEFAULT_CAPITAL,
    slippage: float = DEFAULT_SLIPPAGE,
) -> BacktestResult:
    """
    Run a back-test on *close* prices for *symbol*.

    Parameters
    ----------
    symbol          : ticker string (for labelling only)
    close           : pd.Series of daily close prices, DatetimeIndex
    strategy        : one of sma_cross | ema_cross | rsi | macd
    params          : strategy-specific parameter dict (see defaults below)
    initial_capital : starting portfolio value in INR
    slippage        : one-way slippage fraction (default 0.05%)

    Returns
    -------
    BacktestResult
    """
    if params is None:
        params = {}

    close = close.dropna().sort_index()
    if len(close) < 60:
        raise ValueError(f"Need at least 60 bars for backtesting, got {len(close)}")

    log.info("run_backtest: symbol=%s strategy=%s params=%s", symbol, strategy, params)

    if strategy == "sma_cross":
        p = {"fast": 20, "slow": 50, **params}
        signals = _signals_sma_cross(close, p["fast"], p["slow"])

    elif strategy == "ema_cross":
        p = {"fast": 12, "slow": 26, **params}
        signals = _signals_ema_cross(close, p["fast"], p["slow"])

    elif strategy == "rsi":
        p = {"period": 14, "oversold": 30, "overbought": 70, **params}
        signals = _signals_rsi(close, p["period"], p["oversold"], p["overbought"])

    elif strategy == "macd":
        p = {"fast": 12, "slow": 26, **params}
        signals = _signals_macd(close, p["fast"], p["slow"])

    else:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    equity, drawdown, trade_log = _simulate(close, signals, initial_capital, slippage)

    return BacktestResult(
        symbol=symbol,
        strategy=strategy,
        params=p,
        equity_curve=equity,
        drawdown=drawdown,
        trade_log=trade_log,
    )
