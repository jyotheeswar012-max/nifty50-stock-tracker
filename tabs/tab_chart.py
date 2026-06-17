"""Tab 5 — Detailed Stock Chart."""
import streamlit as st

from utils.logger import get_logger
from utils.constants import NIFTY50
from utils.data import fetch_ticker
from utils.calculations import safe_float
from utils.charts import build_price_chart
from utils.export import export_buttons

log = get_logger(__name__)


def render(market_open: bool, market_status: str, last_close_label: str) -> None:
    from utils.app_helpers import hero, closed_banner, divider
    hero("Stock Chart", "Detailed chart for any Nifty 50 stock")
    closed_banner(market_open, market_status, last_close_label)

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        sc_name = st.selectbox("Stock", [s["name"] for s in NIFTY50], key="sc_s")
    with c2:
        sc_per = st.selectbox(
            "Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2, key="sc_p"
        )
    with c3:
        sc_ct = st.radio("Chart", ["Line", "Candlestick", "Area"],
                         horizontal=True, key="sc_ct")

    sc_sym = next(s["symbol"] for s in NIFTY50 if s["name"] == sc_name)

    with st.spinner(f"Loading {sc_name} — {sc_per}\u2026"):
        try:
            sc_h = fetch_ticker(sc_sym, sc_per)
        except OSError as exc:
            log.error("tab_chart: network error for '%s': %s", sc_sym, exc, exc_info=True)
            st.error("Network error — could not fetch chart data.")
            return
        except Exception as exc:
            log.error("tab_chart: unexpected error for '%s': %s", sc_sym, exc, exc_info=True)
            st.error("Could not load stock data.")
            return

    if sc_h.empty or "Close" not in sc_h.columns:
        log.warning("tab_chart: empty DataFrame symbol='%s' period='%s'", sc_sym, sc_per)
        st.warning("No data found for this stock.")
        return

    c = safe_float(sc_h["Close"].iloc[-1])
    p = safe_float(sc_h["Close"].iloc[-2]) if len(sc_h) > 1 else c
    ch = c - p
    pt = ch / p * 100 if p else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Price" if market_open else "Last Close", "Rs." + format(c, ",.2f"))
    m2.metric("Change", format(ch, "+.2f"), delta=format(pt, "+.2f") + "%")
    m3.metric("High", "Rs." + format(safe_float(sc_h["High"].max()), ",.2f"))
    m4.metric("Low",  "Rs." + format(safe_float(sc_h["Low"].min()), ",.2f"))
    divider()

    try:
        fig = build_price_chart(sc_h, sc_name, sc_per, sc_ct, height=440)
        fig.update_layout(autosize=True)
        st.plotly_chart(fig, use_container_width=True)
    except ValueError as exc:
        log.error("tab_chart: chart ValueError for '%s': %s", sc_sym, exc, exc_info=True)
        st.info("Chart unavailable — invalid data.")
    except Exception as exc:
        log.error("tab_chart: chart unexpected for '%s': %s", sc_sym, exc, exc_info=True)
        st.info("Chart unavailable.")

    divider()
    export_buttons(
        sc_h,
        filename_stem=f"{sc_sym.replace('.NS', '')}_{sc_per}",
        title=f"{sc_name} OHLCV — {sc_per}",
        key_suffix=f"chart_{sc_sym}_{sc_per}",
    )
