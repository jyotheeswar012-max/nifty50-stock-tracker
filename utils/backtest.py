"""
utils/backtest.py  –  Vectorised backtesting engine v2

Strategies included:
  • SMA Crossover
  • RSI Mean-Reversion
  • Bollinger-Band Breakout
  • MACD Signal-Line Cross

All strategies return a pd.Series of signals: 1=long, -1=short, 0=flat.
run_backtest() is fully vectorised (no Python loops over rows).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Callable, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.Series
    benchmark_curve: pd.Series        # buy-and-hold for comparison
    total_return_pct: float
    benchmark_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate_pct: float
    avg_trade_return_pct: float
    num_trades: int
    profit_factor: float


# ─────────────────────────────────────────────────────────────────────────────
# Core engine
# ─────────────────────────────────────────────────────────────────────────────
def run_backtest(
    price_df: pd.DataFrame,            # must have at least 'Close'; optionally 'Volume'
    strategy_fn: Callable,
    initial_capital: float = 100_000.0,
    commission_pct: float = 0.001,     # 0.10 % per leg (NSE realistic)
    slippage_pct: float = 0.0005,      # 0.05 % slippage per leg
    strategy_kwargs: Optional[dict] = None,
) -> BacktestResult:
    """
    Fully vectorised backtester.

    * price_df  – DataFrame with a DatetimeIndex and at least a 'Close' column.
    * strategy_fn(df, **kwargs) must return a pd.Series of integer signals
      aligned to df.index:  1 = long,  -1 = short/exit,  0 = flat/hold.
    """
    kwargs = strategy_kwargs or {}
    df = price_df.copy()
    df.index = pd.to_datetime(df.index)

    signals = strategy_fn(df, **kwargs).reindex(df.index).fillna(0).astype(int)
    # Forward-fill positions (hold until explicit exit)
    pos = signals.replace(0, np.nan).ffill().fillna(0)

    # Daily returns
    close = df["Close"]
    daily_ret = close.pct_change().fillna(0)

    # Strategy daily return = position(t-1) * market_return(t) minus friction on trade days
    pos_lagged = pos.shift(1).fillna(0)
    trade_days = pos.diff().abs() > 0
    friction = trade_days * (commission_pct + slippage_pct)
    strat_ret = pos_lagged * daily_ret - friction

    equity = (1 + strat_ret).cumprod() * initial_capital
    benchmark = (1 + daily_ret).cumprod() * initial_capital

    # ── Drawdown ──
    roll_max = equity.cummax()
    drawdown_series = (equity - roll_max) / roll_max * 100
    max_dd = drawdown_series.min()

    # ── Risk metrics ──
    ann = 252
    excess = strat_ret - 0.065 / ann          # 6.5 % risk-free (India)
    sharpe = excess.mean() / excess.std() * np.sqrt(ann) if excess.std() > 0 else 0.0
    downside = strat_ret[strat_ret < 0].std()
    sortino = (strat_ret.mean() / downside * np.sqrt(ann)) if downside > 0 else 0.0
    total_ret = (equity.iloc[-1] / initial_capital - 1) * 100
    calmar = total_ret / abs(max_dd) if max_dd != 0 else 0.0

    # ── Trade log ──
    trades = _extract_trades(pos, close, commission_pct, slippage_pct)
    win_rate = (trades["pnl"] > 0).mean() * 100 if len(trades) > 0 else 0.0
    avg_ret = trades["return_pct"].mean() if len(trades) > 0 else 0.0
    gross_profit = trades.loc[trades["pnl"] > 0, "pnl"].sum()
    gross_loss = trades.loc[trades["pnl"] < 0, "pnl"].abs().sum()
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    bench_ret = (benchmark.iloc[-1] / initial_capital - 1) * 100

    return BacktestResult(
        trades=trades,
        equity_curve=equity,
        benchmark_curve=benchmark,
        total_return_pct=round(total_ret, 2),
        benchmark_return_pct=round(bench_ret, 2),
        max_drawdown_pct=round(max_dd, 2),
        sharpe_ratio=round(sharpe, 3),
        sortino_ratio=round(sortino, 3),
        calmar_ratio=round(calmar, 3),
        win_rate_pct=round(win_rate, 1),
        avg_trade_return_pct=round(avg_ret, 2),
        num_trades=len(trades),
        profit_factor=round(profit_factor, 2),
    )


def _extract_trades(
    positions: pd.Series,
    prices: pd.Series,
    commission_pct: float,
    slippage_pct: float,
) -> pd.DataFrame:
    """Builds a trade-by-trade log from a positions series."""
    rows = []
    in_trade = False
    entry_date = entry_price = None

    for date, (pos, price) in zip(positions.index, zip(positions, prices)):
        if not in_trade and pos == 1:
            in_trade = True
            entry_date = date
            entry_price = price * (1 + commission_pct + slippage_pct)
        elif in_trade and pos != 1:
            exit_price = price * (1 - commission_pct - slippage_pct)
            pnl = exit_price - entry_price
            rows.append({
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "pnl": round(pnl, 2),
                "return_pct": round(pnl / entry_price * 100, 2),
                "days_held": (date - entry_date).days,
            })
            in_trade = False

    cols = ["entry_date", "exit_date", "entry_price", "exit_price",
            "pnl", "return_pct", "days_held"]
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


# ─────────────────────────────────────────────────────────────────────────────
# Built-in strategies
# ─────────────────────────────────────────────────────────────────────────────
def sma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """Buy when fast SMA > slow SMA; exit when fast < slow."""
    c = df["Close"]
    sig = pd.Series(0, index=df.index)
    sig[c.rolling(fast).mean() > c.rolling(slow).mean()] = 1
    sig[c.rolling(fast).mean() < c.rolling(slow).mean()] = -1
    return sig


def rsi_strategy(
    df: pd.DataFrame, period: int = 14,
    oversold: float = 30.0, overbought: float = 70.0
) -> pd.Series:
    """Buy on RSI < oversold; sell on RSI > overbought."""
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    sig = pd.Series(0, index=df.index)
    sig[rsi < oversold] = 1
    sig[rsi > overbought] = -1
    return sig


def bollinger_breakout(
    df: pd.DataFrame, period: int = 20, std_dev: float = 2.0
) -> pd.Series:
    """Buy on upper-band breakout; exit on lower-band touch."""
    c = df["Close"]
    mid = c.rolling(period).mean()
    band = c.rolling(period).std() * std_dev
    upper, lower = mid + band, mid - band
    sig = pd.Series(0, index=df.index)
    sig[c > upper] = 1
    sig[c < lower] = -1
    return sig


def macd_strategy(
    df: pd.DataFrame,
    fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.Series:
    """Buy on MACD line crossing above signal; sell on cross below."""
    c = df["Close"]
    ema_fast = c.ewm(span=fast, adjust=False).mean()
    ema_slow = c.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    sig = pd.Series(0, index=df.index)
    sig[macd_line > signal_line] = 1
    sig[macd_line < signal_line] = -1
    return sig


STRATEGIES: dict[str, Callable] = {
    "SMA Crossover": sma_crossover,
    "RSI Mean-Reversion": rsi_strategy,
    "Bollinger Breakout": bollinger_breakout,
    "MACD Signal": macd_strategy,
}
