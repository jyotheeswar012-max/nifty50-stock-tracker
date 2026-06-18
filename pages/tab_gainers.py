"""Tab 3 — Gainers & Losers."""
import streamlit as st

from utils.logger import get_logger
from utils.charts import build_pct_bar

log = get_logger(__name__)


def render(market_open, market_status, last_close_label, build_stock_rows_cached):
    from utils.app_helpers import hero, closed_banner, divider
    hero("Gainers & Losers", "Today's top movers" if market_open else "Last session movers")
    closed_banner(market_open, market_status, last_close_label)

    with st.spinner("Loading…"):
        try:
            df = build_stock_rows_cached()
        except Exception as exc:
            log.error("tab_gainers: build_stock_rows_cached failed: %s", exc, exc_info=True)
            st.error("Could not load stock data.")
            return

    if "_pct" not in df.columns:
        st.warning("No percentage change data available.")
        return

    df_valid = df[df["_pct"].notna()].copy()
    df_sorted = df_valid.sort_values("_pct", ascending=False)

    top_n = st.slider("Top N per side", 5, 25, 10, key="gn_n")
    gainers = df_sorted.head(top_n)
    losers  = df_sorted.tail(top_n).sort_values("_pct")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📈 Top Gainers")
        st.dataframe(gainers[["Symbol", "Name", "Change (%)", "_pct"]]
                     .rename(columns={"_pct": "Pct"}),
                     use_container_width=True, hide_index=True)
    with c2:
        st.markdown("### 📉 Top Losers")
        st.dataframe(losers[["Symbol", "Name", "Change (%)", "_pct"]]
                     .rename(columns={"_pct": "Pct"}),
                     use_container_width=True, hide_index=True)

    divider()
    title = "% Change — Top Gainers & Losers" + (" (live)" if market_open else " (last session)")
    combined = gainers._append(losers).drop_duplicates(subset=["Symbol"])
    try:
        fig = build_pct_bar(combined, "Symbol", "_pct", title, text_col="Change (%)")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        log.error("tab_gainers: bar chart failed: %s", exc, exc_info=True)
