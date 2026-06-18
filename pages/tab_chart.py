"""Tab 5 — Stock Chart."""
import streamlit as st

from utils.logger import get_logger
from utils.data import fetch_ticker
from utils.charts import build_price_chart, build_volume_chart
from utils.constants import NIFTY50
from utils.calculations import safe_float

log = get_logger(__name__)


def render(market_open, market_status, last_close_label):
    from utils.app_helpers import hero, closed_banner, divider
    hero("Stock Chart", "Detailed OHLCV chart for any Nifty 50 stock")
    closed_banner(market_open, market_status, last_close_label)

    symbols = [s["symbol"] for s in NIFTY50]
    names   = [s["name"]   for s in NIFTY50]
    options = [f"{sym} — {nm}" for sym, nm in zip(symbols, names)]

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        sel = st.selectbox("Stock", options, key="ch_sym")
    with c2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=1, key="ch_p")
    with c3:
        chart_type = st.radio("Type", ["Line", "Candlestick", "Area"], key="ch_t")

    sym = symbols[options.index(sel)]
    name = names[options.index(sel)]

    try:
        df = fetch_ticker(sym, period)
    except Exception as exc:
        log.error("tab_chart: fetch error for %s: %s", sym, exc, exc_info=True)
        st.error("Could not fetch data.")
        return

    if df.empty or "Close" not in df.columns:
        st.warning("No data available.")
        return

    c = safe_float(df["Close"].iloc[-1])
    p = safe_float(df["Close"].iloc[-2]) if len(df) > 1 else c
    ch = c - p
    pt = ch / p * 100 if p else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Price" if market_open else "Last Close", f"Rs.{c:,.2f}")
    m2.metric("Change", f"{ch:+.2f}", delta=f"{pt:+.2f}%")
    m3.metric("Period High", f"Rs.{safe_float(df['High'].max()):,.2f}")
    m4.metric("Period Low",  f"Rs.{safe_float(df['Low'].min()):,.2f}")
    divider()

    try:
        fig = build_price_chart(df, name, period, chart_type, height=440)
        fig.update_layout(autosize=True)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        log.error("tab_chart: price chart error: %s", exc, exc_info=True)
        st.info("Price chart unavailable.")

    divider()
    try:
        fig_v = build_volume_chart(df, name, height=220)
        fig_v.update_layout(autosize=True)
        st.plotly_chart(fig_v, use_container_width=True)
    except Exception as exc:
        log.error("tab_chart: volume chart error: %s", exc, exc_info=True)
