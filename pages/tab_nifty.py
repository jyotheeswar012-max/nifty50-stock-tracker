"""Tab 1 — Nifty 50 Index detail."""
import streamlit as st

from utils.logger import get_logger
from utils.data import fetch_ticker
from utils.calculations import safe_float
from utils.charts import build_price_chart

log = get_logger(__name__)


def render(market_open: bool, market_status: str, last_close_label: str) -> None:
    from utils.app_helpers import hero, divider, closed_banner
    hero("Nifty 50 Index", "^NSEI — NSE Flagship Index")
    closed_banner(market_open, market_status, last_close_label)

    c1, c2 = st.columns([1, 3])
    with c1:
        n_period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="nf_p")
    with c2:
        chart_type = st.radio("Chart", ["Line", "Candlestick", "Area"], horizontal=True, key="nf_ct")

    try:
        nifty = fetch_ticker("^NSEI", n_period)
    except Exception as exc:
        log.error("tab_nifty: error fetching ^NSEI: %s", exc, exc_info=True)
        st.error("Could not load Nifty 50 data.")
        return

    if nifty.empty or "Close" not in nifty.columns:
        st.warning("Could not fetch Nifty 50 data.")
        return

    c = safe_float(nifty["Close"].iloc[-1])
    p = safe_float(nifty["Close"].iloc[-2]) if len(nifty) > 1 else c
    ch = c - p
    pt = ch / p * 100 if p else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Price" if market_open else "Last Close", "Rs." + format(c, ",.2f"))
    m2.metric("Change", format(ch, "+.2f"), delta=format(pt, "+.2f") + "%")
    m3.metric("Period High", "Rs." + format(safe_float(nifty["High"].max()), ",.2f"))
    m4.metric("Period Low", "Rs." + format(safe_float(nifty["Low"].min()), ",.2f"))
    m5.metric("Avg Volume", format(int(safe_float(nifty["Volume"].mean())), ","))
    divider()

    try:
        fig = build_price_chart(nifty, "Nifty 50", n_period, chart_type, y_title="Index Value", height=440)
        fig.update_layout(autosize=True)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        log.error("tab_nifty: chart error: %s", exc, exc_info=True)
        st.info("Chart unavailable.")
