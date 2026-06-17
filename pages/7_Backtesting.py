"""
pages/7_Backtesting.py  —  Paper Portfolio Back-tester UI.

Allows users to:
  • Pick any Nifty 50 symbol and date range
  • Choose a strategy (SMA cross, EMA cross, RSI, MACD)
  • Tune strategy parameters with sliders
  • View equity curve, drawdown chart, key metrics, and full trade log
  • Download the trade log as CSV
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from utils.backtest import DEFAULT_CAPITAL, StrategyName, run_backtest
from utils.constants import NIFTY50
from utils.data import fetch_ticker

st.set_page_config(page_title="Backtesting", page_icon="📈", layout="wide")
st.title("📈 Strategy Back-tester")
st.caption("Vectorised back-test on 5-year historical closes. Slippage: 0.05 % per side.")

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Parameters")
    symbols = [s["symbol"] for s in NIFTY50]
    symbol  = st.selectbox("Symbol", symbols, index=symbols.index("RELIANCE.NS") if "RELIANCE.NS" in symbols else 0)

    strategy: StrategyName = st.selectbox(  # type: ignore[assignment]
        "Strategy",
        ["sma_cross", "ema_cross", "rsi", "macd"],
        format_func=lambda x: {
            "sma_cross": "SMA Crossover",
            "ema_cross": "EMA Crossover",
            "rsi":       "RSI Mean-Reversion",
            "macd":      "MACD Signal Cross",
        }[x],
    )

    params: dict = {}
    if strategy in ("sma_cross", "ema_cross"):
        params["fast"] = st.slider("Fast window", 5,  50,  20 if strategy == "sma_cross" else 12)
        params["slow"] = st.slider("Slow window", 20, 200, 50 if strategy == "sma_cross" else 26)
    elif strategy == "rsi":
        params["period"]     = st.slider("RSI period",     5,  30, 14)
        params["oversold"]   = st.slider("Oversold level", 10, 40, 30)
        params["overbought"] = st.slider("Overbought level", 60, 90, 70)
    elif strategy == "macd":
        params["fast"] = st.slider("Fast EMA", 5,  20, 12)
        params["slow"] = st.slider("Slow EMA", 15, 50, 26)

    capital   = st.number_input("Starting capital (INR)", 10_000, 10_000_000, DEFAULT_CAPITAL, step=10_000)
    slippage  = st.slider("Slippage per side (%)", 0.0, 0.5, 0.05, step=0.01) / 100
    run_btn   = st.button("▶️  Run Back-test", use_container_width=True)

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------
if not run_btn:
    st.info("👈 Configure parameters in the sidebar and click **Run Back-test**.")
    st.stop()

with st.spinner(f"Fetching 5-year history for {symbol}…"):
    df = fetch_ticker(symbol, period="5y")

if df.empty:
    st.error(f"Could not fetch data for {symbol}. Try again in a moment.")
    st.stop()

try:
    result = run_backtest(
        symbol=symbol,
        close=df["Close"],
        strategy=strategy,
        params=params,
        initial_capital=capital,
        slippage=slippage,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------
m = result.metrics
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("CAGR",          f"{m.get('cagr', 0):.1f} %")
col2.metric("Sharpe",        f"{m.get('sharpe', 0):.2f}")
col3.metric("Max Drawdown",  f"{m.get('max_drawdown', 0):.1f} %")
col4.metric("Win Rate",      f"{m.get('win_rate', 0):.1f} %")
col5.metric("Total Trades",  str(m.get("total_trades", 0)))
col6.metric("Avg Hold Days", f"{m.get('avg_hold_days', 0):.0f} d")

st.divider()

# ---------------------------------------------------------------------------
# Equity curve + drawdown chart
# ---------------------------------------------------------------------------
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    row_heights=[0.7, 0.3],
    vertical_spacing=0.04,
    subplot_titles=("Equity Curve", "Drawdown"),
)

fig.add_trace(
    go.Scatter(
        x=result.equity_curve.index,
        y=result.equity_curve.values,
        mode="lines",
        name="Strategy",
        line=dict(color="#01696f", width=2),
    ),
    row=1, col=1,
)

# Buy-and-hold baseline
bah_equity = capital * (df["Close"] / df["Close"].iloc[0])
fig.add_trace(
    go.Scatter(
        x=bah_equity.index,
        y=bah_equity.values,
        mode="lines",
        name="Buy & Hold",
        line=dict(color="#aaaaaa", width=1.5, dash="dot"),
    ),
    row=1, col=1,
)

fig.add_trace(
    go.Scatter(
        x=result.drawdown.index,
        y=result.drawdown.values * 100,
        mode="lines",
        name="Drawdown %",
        fill="tozeroy",
        line=dict(color="#a12c7b", width=1),
        fillcolor="rgba(161,44,123,0.15)",
    ),
    row=2, col=1,
)

fig.update_layout(
    height=550,
    legend=dict(orientation="h", y=1.02, x=0),
    margin=dict(t=30, b=10),
    hovermode="x unified",
)
fig.update_yaxes(title_text="Portfolio value (INR)", row=1, col=1)
fig.update_yaxes(title_text="Drawdown %", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Trade log
# ---------------------------------------------------------------------------
if result.trade_log.empty:
    st.info("No completed round-trips in this back-test period.")
else:
    st.subheader(f"Trade Log ({len(result.trade_log)} trades)")
    styled = result.trade_log.copy()
    styled["entry_date"] = pd.to_datetime(styled["entry_date"]).dt.strftime("%d %b %Y")
    styled["exit_date"]  = pd.to_datetime(styled["exit_date"]).dt.strftime("%d %b %Y")
    st.dataframe(
        styled.style.applymap(
            lambda v: "color: #437a22" if isinstance(v, str) and v == "win"
            else ("color: #a12c7b" if isinstance(v, str) and v == "loss" else ""),
            subset=["result"],
        ),
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = result.trade_log.to_csv(index=False).encode()
    st.download_button(
        "⬇️  Download trade log CSV",
        data=csv_bytes,
        file_name=f"backtest_{symbol}_{strategy}.csv",
        mime="text/csv",
    )
