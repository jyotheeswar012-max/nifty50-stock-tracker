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
    _build_static_history,
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


def _get_history() -> tuple[dict, bool]:
    try:
        from utils.data import fetch_all_history
        hist = fetch_all_history()
        if hist and len(hist) >= 10:
            return hist, True
    except Exception as exc:
        log.warning("tab_companies: fetch_all_history failed: %s", exc)
    return _build_static_history(), False


def _build_pie_from_history(history: dict, title: str) -> object:
    rows = []
    for s in NIFTY50:
        h = history.get(s["symbol"])
        if h is not None and not h.empty and "Close" in h.columns:
            close_series = h["Close"].dropna()
            price = float(close_series.iloc[-1]) if not close_series.empty else 1000.0
        else:
            price = 1000.0
        rows.append({"Sector": s["sector"], "_curr": price})
    return build_sector_pie(pd.DataFrame(rows), title=title)


def render(market_open, market_status, last_close_label, build_stock_rows_cached):
    from utils.app_helpers import hero, closed_banner, sec, divider
    hero("All 50 Companies", "Live prices" if market_open else "Last closing prices")
    closed_banner(market_open, market_status, last_close_label)

    sectors = ["All"] + sorted({s["sector"] for s in NIFTY50})
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")

    with st.spinner("Loading stock data…"):
        try:
            df_rows = build_stock_rows_cached()
        except Exception as exc:
            log.error("tab_companies: build_stock_rows_cached failed: %s", exc, exc_info=True)
            st.error("Could not load stock data.")
            return

    df_filtered = df_rows[df_rows["Sector"] == sel_sec] if sel_sec != "All" else df_rows
    display_df = _sanitize_numeric_cols(df_filtered.drop(columns=["_curr", "_pct"], errors="ignore"))
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    export_buttons(display_df, filename_stem=f"nifty50_{'all' if sel_sec == 'All' else sel_sec.replace(' ', '_')}",
                   title=f"Nifty 50 Companies — {sel_sec}", key_suffix="companies")
    divider()

    with st.spinner("Loading price history…"):
        all_hist, is_live = _get_history()

    if not is_live:
        st.info("⚠️ Live market history unavailable. Charts below use representative synthetic data.")

    if sel_sec != "All":
        sector_syms  = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
        sector_names = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
    else:
        sector_syms  = SYMBOLS
        sector_names = [s["name"] for s in NIFTY50]

    sec("Sector Allocation")
    try:
        fig_pie = _build_pie_from_history(all_hist, "Sector Allocation — Nifty 50")
        if fig_pie.data:
            st.plotly_chart(fig_pie, use_container_width=True)
    except Exception as exc:
        log.error("tab_companies: sector pie failed: %s", exc, exc_info=True)
    divider()

    if "_pct" in df_filtered.columns:
        valid = df_filtered[df_filtered["_pct"].notna()].copy()
        if not valid.empty:
            try:
                fig = build_pct_bar(valid, "Symbol", "_pct",
                                    "1-Day % Change" if market_open else "1-Day % Change (last session)",
                                    text_col="Change (%)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                log.error("tab_companies: bar chart failed: %s", exc, exc_info=True)
    divider()

    sec("30-Day Return Correlation Heatmap")
    try:
        hm_height = max(400, min(700, len(sector_syms) * 14 + 120))
        fig_hm = build_correlation_heatmap(all_hist, sector_syms, sector_names,
                                            title=f"30-Day Correlation — {sel_sec}", height=hm_height)
        if fig_hm.data:
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Not enough data to compute correlations.")
    except Exception as exc:
        log.error("tab_companies: heatmap failed: %s", exc, exc_info=True)
    divider()

    sec("20-Day Price Sparklines")
    try:
        spark_height = max(300, (len(sector_syms) // 5 + 1) * 110)
        fig_spark = build_sparkline_table(all_hist, sector_syms, sector_names, height=spark_height)
        if fig_spark.data:
            st.plotly_chart(fig_spark, use_container_width=True)
        else:
            st.info("No sparkline data available.")
    except Exception as exc:
        log.error("tab_companies: sparklines failed: %s", exc, exc_info=True)
