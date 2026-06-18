"""Tab 3 — Top Gainers & Losers."""
import pandas as pd
import streamlit as st

from utils.logger import get_logger
from utils.calculations import safe_sort
from utils.charts import build_pct_bar

log = get_logger(__name__)


def render(
    market_open: bool,
    market_status: str,
    last_close_label: str,
    build_stock_rows_cached,
) -> None:
    from utils.app_helpers import hero, closed_banner, sec
    hero("Gainers & Losers", "Today" if market_open else "Last Session")
    closed_banner(market_open, market_status, last_close_label)

    try:
        df_rows = build_stock_rows_cached()
    except Exception as exc:
        log.error("tab_gainers: build_stock_rows_cached failed: %s", exc, exc_info=True)
        st.error("Could not load stock data.")
        return

    valid = df_rows[df_rows["_pct"].notna()].copy()
    top_n = st.slider("Top N", 3, 10, 5, key="gl_n")

    if valid.empty:
        log.warning("tab_gainers: no valid pct rows available")
        st.warning("No data available.")
        return

    gainers = safe_sort(valid, "_pct", ascending=False).head(top_n)
    losers = safe_sort(valid, "_pct", ascending=True).head(top_n)
    price_col = next(
        (c for c in df_rows.columns if "Price" in c or "Last Close" in c), "_curr"
    )

    display_cols = ["Symbol", "Company", price_col, "Change (%)"]
    missing = [c for c in display_cols if c not in df_rows.columns]
    if missing:
        log.error("tab_gainers: expected columns missing from df_rows: %s", missing)
        st.error("Data schema mismatch — missing columns: " + str(missing))
        return

    cg, cl = st.columns(2)
    with cg:
        sec("Top Gainers")
        st.dataframe(gainers[display_cols], use_container_width=True, hide_index=True)
    with cl:
        sec("Top Losers")
        st.dataframe(losers[display_cols], use_container_width=True, hide_index=True)

    try:
        combined = pd.concat([gainers, losers]).drop_duplicates(subset="Symbol")
        fig = build_pct_bar(
            combined[combined["_pct"].notna()],
            "Symbol", "_pct", "Gainers vs Losers", text_col="Change (%)",
        )
        fig.update_layout(autosize=True)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        log.error("tab_gainers: combined bar chart error: %s", exc, exc_info=True)
