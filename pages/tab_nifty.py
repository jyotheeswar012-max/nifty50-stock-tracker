"""Tab 1 — Nifty 50 Index detail."""
from __future__ import annotations

import streamlit as st
from utils.logger import get_logger
from utils.data import fetch_ticker
from utils.calculations import safe_float

log = get_logger(__name__)


def render(market_open: bool, market_status: str, last_close_label: str) -> None:
    from utils.app_helpers import hero, closed_banner, sec, divider
    from utils.charts import build_price_chart

    hero("📈 Nifty 50 Index", "Live index chart & stats")
    closed_banner(market_open, market_status, last_close_label)

    c1, c2 = st.columns([2, 1])
    with c1:
        period = st.selectbox(
            "Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="nifty_period"
        )
    with c2:
        chart_type = st.radio(
            "Chart type", ["Line", "Candlestick", "Area"],
            horizontal=True, key="nifty_ct"
        )

    with st.spinner("Loading Nifty 50 data…"):
        try:
            df = fetch_ticker("^NSEI", period)
        except Exception as exc:
            log.error("tab_nifty: fetch failed: %s", exc, exc_info=True)
            st.error("Could not fetch Nifty 50 data.")
            return

    if df.empty or "Close" not in df.columns:
        st.warning("No data available for Nifty 50.")
        return

    close = safe_float(df["Close"].iloc[-1])
    prev  = safe_float(df["Close"].iloc[-2]) if len(df) > 1 else close
    chg   = close - prev
    pct   = (chg / prev * 100) if prev else 0.0
    hi    = safe_float(df["High"].max())
    lo    = safe_float(df["Low"].min())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Index" if market_open else "Last Close", f"₹{close:,.2f}")
    m2.metric("Change", f"{chg:+.2f}", delta=f"{pct:+.2f}%")
    m3.metric(f"Period High", f"₹{hi:,.2f}")
    m4.metric(f"Period Low",  f"₹{lo:,.2f}")

    divider()

    try:
        fig = build_price_chart(df, "Nifty 50", period, chart_type, height=460)
        fig.update_layout(autosize=True)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        log.error("tab_nifty: chart build failed: %s", exc, exc_info=True)
        st.line_chart(df["Close"])

    divider()
    sec("Raw OHLCV Data")
    st.dataframe(
        df[["Open", "High", "Low", "Close", "Volume"]].tail(30).sort_index(ascending=False),
        use_container_width=True,
    )
