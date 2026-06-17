"""
pages/7_Backtesting.py  –  Backtesting UI v2

Features:
  • 4 built-in strategies (SMA, RSI, Bollinger, MACD)
  • Per-strategy parameter sliders
  • Equity curve vs buy-and-hold benchmark
  • Full metrics dashboard (Sharpe, Sortino, Calmar, Drawdown, Win Rate, Profit Factor)
  • Trade log table with colour coding
  • CSV export of trades
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.backtest import run_backtest, STRATEGIES
from utils.data import get_stock_history
from utils.constants import NIFTY50_SYMBOLS
from utils.auth_ui import require_login

require_login()

st.set_page_config(page_title="Backtesting", page_icon="📊", layout="wide")
st.title("📊 Strategy Backtesting")
st.caption("Test trading strategies on historical Nifty 50 data. Past performance does not guarantee future results.")

# ── Sidebar controls ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Parameters")

    symbol = st.selectbox("Stock Symbol", options=NIFTY50_SYMBOLS, index=0)
    period_map = {"6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "3 Years": "3y"}
    period_label = st.selectbox("Lookback Period", list(period_map.keys()), index=1)
    period = period_map[period_label]

    strategy_name = st.selectbox("Strategy", list(STRATEGIES.keys()))
    capital = st.number_input("Initial Capital (₹)", value=100_000, step=10_000, min_value=10_000)
    commission = st.slider("Commission (%)", 0.01, 0.5, 0.10, 0.01) / 100
    slippage = st.slider("Slippage (%)", 0.01, 0.25, 0.05, 0.01) / 100

    st.divider()
    st.subheader("Strategy Parameters")
    strat_kwargs = {}
    if strategy_name == "SMA Crossover":
        strat_kwargs["fast"] = st.slider("Fast SMA", 5, 50, 20)
        strat_kwargs["slow"] = st.slider("Slow SMA", 20, 200, 50)
    elif strategy_name == "RSI Mean-Reversion":
        strat_kwargs["period"] = st.slider("RSI Period", 7, 28, 14)
        strat_kwargs["oversold"] = st.slider("Oversold Threshold", 10, 40, 30)
        strat_kwargs["overbought"] = st.slider("Overbought Threshold", 60, 90, 70)
    elif strategy_name == "Bollinger Breakout":
        strat_kwargs["period"] = st.slider("BB Period", 10, 50, 20)
        strat_kwargs["std_dev"] = st.slider("Std Dev Multiplier", 1.0, 3.0, 2.0, 0.1)
    elif strategy_name == "MACD Signal":
        strat_kwargs["fast"] = st.slider("MACD Fast", 5, 20, 12)
        strat_kwargs["slow"] = st.slider("MACD Slow", 15, 40, 26)
        strat_kwargs["signal"] = st.slider("Signal Period", 5, 15, 9)

    run_btn = st.button("▶ Run Backtest", type="primary", use_container_width=True)

# ── Main panel ────────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner(f"Fetching {symbol} history ({period_label})..."):
        df = get_stock_history(symbol, period=period)

    if df is None or df.empty:
        st.error(f"No data available for **{symbol}**. Try a different period or check your internet connection.")
        st.stop()

    with st.spinner("Running backtest..."):
        result = run_backtest(
            df,
            strategy_fn=STRATEGIES[strategy_name],
            initial_capital=float(capital),
            commission_pct=commission,
            slippage_pct=slippage,
            strategy_kwargs=strat_kwargs,
        )

    # ── Metrics ──
    st.subheader("Performance Summary")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    delta_vs_bench = result.total_return_pct - result.benchmark_return_pct
    c1.metric("Total Return", f"{result.total_return_pct:.2f}%",
              delta=f"{delta_vs_bench:+.2f}% vs B&H")
    c2.metric("Max Drawdown", f"{result.max_drawdown_pct:.2f}%")
    c3.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
    c4.metric("Sortino Ratio", f"{result.sortino_ratio:.2f}")
    c5.metric("Win Rate", f"{result.win_rate_pct:.1f}%")
    c6.metric("Profit Factor", f"{result.profit_factor:.2f}")

    c7, c8, c9 = st.columns(3)
    c7.metric("Calmar Ratio", f"{result.calmar_ratio:.2f}")
    c8.metric("Trades", result.num_trades)
    c9.metric("Avg Trade Return", f"{result.avg_trade_return_pct:.2f}%")

    # ── Equity curve chart ──
    st.subheader("Equity Curve vs Buy & Hold")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result.equity_curve.index, y=result.equity_curve.values,
        name=strategy_name, line=dict(color="#00C4B4", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=result.benchmark_curve.index, y=result.benchmark_curve.values,
        name="Buy & Hold", line=dict(color="#FF7043", width=1.5, dash="dot"),
    ))
    fig.update_layout(
        xaxis_title="Date", yaxis_title="Portfolio Value (₹)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400, margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Trade log ──
    if not result.trades.empty:
        st.subheader(f"Trade Log ({result.num_trades} trades)")

        def _colour(val):
            if isinstance(val, (int, float)):
                return "color: #4CAF50" if val > 0 else ("color: #F44336" if val < 0 else "")
            return ""

        styled = result.trades.style.applymap(_colour, subset=["pnl", "return_pct"])
        st.dataframe(styled, use_container_width=True, height=300)

        csv = result.trades.to_csv(index=False).encode()
        st.download_button(
            "⬇ Download Trade Log (CSV)", csv,
            file_name=f"backtest_{symbol}_{strategy_name.replace(' ','_')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No completed trades in the selected period.")
else:
    st.info("Configure parameters in the sidebar and click **▶ Run Backtest** to begin.")
