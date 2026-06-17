"""Tab 2 — All 50 Companies."""
import pandas as pd
import streamlit as st

from utils.logger import get_logger
from utils.constants import NIFTY50, SYMBOLS
from utils.charts import (
    build_pct_bar,
    build_correlation_heatmap,
    build_sparkline_table,
    build_sector_pie,
)
from utils.export import export_buttons

log = get_logger(__name__)

_PURE_NUM = r"^[\-+]?[\d,\.]+$"


def _sanitize_numeric_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != object or df[col].dtype == bool:
            continue
        non_null = df[col].dropna()
        if non_null.empty or df[col].isna().mean() > 0.05:
            continue
        if not non_null.astype(str).str.match(_PURE_NUM).all():
            continue
        try:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="raise",
            )
        except (ValueError, TypeError) as exc:
            log.warning("tab_companies: skipping coercion of '%s': %s", col, exc)
    return df


def render(
    market_open: bool,
    market_status: str,
    last_close_label: str,
    build_stock_rows_cached,
) -> None:
    from utils.app_helpers import hero, closed_banner, sec, divider
    hero("All 50 Companies",
         "Live prices" if market_open else "Last closing prices")
    closed_banner(market_open, market_status, last_close_label)

    sectors = ["All"] + sorted({s["sector"] for s in NIFTY50})
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")

    # ── Spinner: heavy cached build ───────────────────────────────────────────
    with st.spinner("Loading stock data\u2026"):
        try:
            df_rows = build_stock_rows_cached()
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: build_stock_rows_cached failed: %s", exc, exc_info=True)
            st.error("Could not load stock data.")
            return

    if sel_sec != "All":
        df_rows = df_rows[df_rows["Sector"] == sel_sec]

    display_df = _sanitize_numeric_cols(
        df_rows.drop(columns=["_curr", "_pct"], errors="ignore")
    )
    st.dataframe(display_df, width="stretch", hide_index=True)

    # Export buttons directly below the table
    export_buttons(
        display_df,
        filename_stem=f"nifty50_{'all' if sel_sec == 'All' else sel_sec.replace(' ', '_')}",
        title=f"Nifty 50 Companies \u2014 {sel_sec}",
        key_suffix="companies",
    )

    divider()

    # ── Sector Allocation Pie ──────────────────────────────────────────────────
    sec("Sector Allocation")
    st.caption(
        "Donut chart weighted by current price sum per sector. "
        "Falls back to stock count if price data is unavailable."
    )
    try:
        # Use the full (unfiltered by sector) df_rows for a meaningful pie
        all_rows = build_stock_rows_cached()
        pie_title = (
            "Sector Allocation \u2014 Nifty 50"
            if sel_sec == "All"
            else f"Sector Allocation \u2014 {sel_sec} highlighted"
        )
        fig_pie = build_sector_pie(all_rows, title=pie_title)
        if fig_pie.data:
            fig_pie.update_layout(autosize=True)
            st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info("Not enough data to render sector pie.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: sector pie failed: %s", exc, exc_info=True)

    divider()

    valid = df_rows[df_rows["_pct"].notna()].copy()
    if not valid.empty:
        try:
            title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
            fig = build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)")
            fig.update_layout(autosize=True)
            st.plotly_chart(fig, width="stretch")
        except ValueError as exc:
            log.error("tab_companies: bar chart ValueError: %s", exc, exc_info=True)
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: bar chart unexpected: %s", exc, exc_info=True)

    divider()

    # ── Correlation heatmap ────────────────────────────────────────────────
    sec("30-Day Return Correlation Heatmap")
    st.caption(
        "Pairwise Pearson correlations of daily returns over the last 30 trading sessions. "
        "Blue = negative correlation, red = positive."
    )

    with st.spinner("Computing correlations\u2026"):
        try:
            from utils.data import fetch_all_history
            all_hist = fetch_all_history()
        except OSError as exc:
            log.error("tab_companies: heatmap network error: %s", exc, exc_info=True)
            st.info("Could not load history for correlation heatmap.")
            all_hist = {}
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: heatmap fetch unexpected: %s", exc, exc_info=True)
            all_hist = {}

    if all_hist:
        # Filter symbols to selected sector if applicable
        if sel_sec != "All":
            sector_syms  = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
            sector_names = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
        else:
            sector_syms  = SYMBOLS
            sector_names = [s["name"] for s in NIFTY50]

        try:
            fig_hm = build_correlation_heatmap(
                all_hist, sector_syms, sector_names,
                title=f"30-Day Correlation \u2014 {sel_sec}",
                height=max(400, min(700, len(sector_syms) * 14 + 120)),
            )
            if fig_hm.data:
                fig_hm.update_layout(autosize=True)
                st.plotly_chart(fig_hm, width="stretch")
            else:
                st.info("Not enough overlapping data to compute correlations.")
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: heatmap render failed: %s", exc, exc_info=True)

    divider()

    # ── Sparkline small multiples ──────────────────────────────────────────────
    sec("20-Day Price Sparklines")
    st.caption("Each mini-chart shows the last 20 trading sessions. Green = net gain, red = net loss.")

    if all_hist:
        if sel_sec != "All":
            spark_syms   = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
            spark_labels = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
        else:
            spark_syms   = SYMBOLS
            spark_labels = [s["name"] for s in NIFTY50]

        try:
            fig_spark = build_sparkline_table(
                all_hist, spark_syms, spark_labels,
                height=max(300, (len(spark_syms) // 5 + 1) * 110),
            )
            if fig_spark.data:
                fig_spark.update_layout(autosize=True)
                st.plotly_chart(fig_spark, width="stretch")
            else:
                st.info("No sparkline data available.")
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: sparklines failed: %s", exc, exc_info=True)
