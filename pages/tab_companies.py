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
    """Return (history_dict, is_live).
    Tries live yfinance fetch first; falls back to static synthetic data
    so that the three charts always have something to render.
    """
    try:
        from utils.data import fetch_all_history
        hist = fetch_all_history()
        if hist:
            return hist, True
    except OSError as exc:
        log.warning("tab_companies: network error fetching history: %s", exc)
    except Exception as exc:  # noqa: BLE001
        log.warning("tab_companies: fetch_all_history failed: %s", exc)
    log.info("tab_companies: using static synthetic history fallback")
    return _build_static_history(), False


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

    # ── Stock data table ──────────────────────────────────────────────────────
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
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    export_buttons(
        display_df,
        filename_stem=f"nifty50_{'all' if sel_sec == 'All' else sel_sec.replace(' ', '_')}",
        title=f"Nifty 50 Companies \u2014 {sel_sec}",
        key_suffix="companies",
    )

    from utils.app_helpers import divider as _div
    _div()

    # ── Sector Allocation Pie ─────────────────────────────────────────────────
    sec("Sector Allocation")
    st.caption(
        "Donut chart weighted by current price sum per sector. "
        "Falls back to stock count if price data is unavailable."
    )
    try:
        all_rows = build_stock_rows_cached()
        pie_title = (
            "Sector Allocation \u2014 Nifty 50"
            if sel_sec == "All"
            else f"Sector Allocation \u2014 {sel_sec} highlighted"
        )
        fig_pie = build_sector_pie(all_rows, title=pie_title)
        if fig_pie.data:
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            # Fallback: build sector weights from static seed prices
            static_h = _build_static_history()
            rows = []
            for s in NIFTY50:
                h = static_h.get(s["symbol"])
                price = float(h["Close"].iloc[-1]) if (h is not None and not h.empty) else 0.0
                rows.append({"Sector": s["sector"], "_curr": price})
            fig_pie2 = build_sector_pie(pd.DataFrame(rows), title=pie_title + " (representative)")
            if fig_pie2.data:
                st.caption("\u26a0\ufe0f Showing representative data \u2014 live prices unavailable.")
                st.plotly_chart(fig_pie2, use_container_width=True)
            else:
                st.info("Not enough data to render sector pie.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: sector pie failed: %s", exc, exc_info=True)

    _div()

    # ── 1-Day % Change bar ────────────────────────────────────────────────────
    valid = df_rows[df_rows["_pct"].notna()].copy()
    if not valid.empty:
        try:
            title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
            fig = build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: bar chart failed: %s", exc, exc_info=True)

    _div()

    # ── Fetch history ONCE for both heatmap + sparklines ─────────────────────
    with st.spinner("Loading 30-day price history\u2026"):
        all_hist, is_live = _get_history()

    if not is_live:
        st.info(
            "\u26a0\ufe0f Live market history is unavailable right now. "
            "The charts below use representative synthetic data seeded from "
            "current Nifty 50 prices so you can explore the dashboards."
        )

    # Narrow to selected sector if needed
    if sel_sec != "All":
        sector_syms  = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
        sector_names = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
    else:
        sector_syms  = SYMBOLS
        sector_names = [s["name"] for s in NIFTY50]

    # ── Correlation heatmap ───────────────────────────────────────────────────
    sec("30-Day Return Correlation Heatmap")
    st.caption(
        "Pairwise Pearson correlations of daily returns over the last 30 trading sessions. "
        "Blue\u00a0=\u00a0negative correlation, red\u00a0=\u00a0positive."
    )
    try:
        fig_hm = build_correlation_heatmap(
            all_hist, sector_syms, sector_names,
            title=f"30-Day Correlation \u2014 {sel_sec}",
            height=max(400, min(700, len(sector_syms) * 14 + 120)),
        )
        if fig_hm.data:
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Not enough overlapping data to compute correlations.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: heatmap render failed: %s", exc, exc_info=True)

    _div()

    # ── 20-Day Sparklines ─────────────────────────────────────────────────────
    sec("20-Day Price Sparklines")
    st.caption(
        "Each mini-chart shows the last 20 trading sessions. "
        "Green\u00a0=\u00a0net gain, red\u00a0=\u00a0net loss."
    )
    try:
        fig_spark = build_sparkline_table(
            all_hist, sector_syms, sector_names,
            height=max(300, (len(sector_syms) // 5 + 1) * 110),
        )
        if fig_spark.data:
            st.plotly_chart(fig_spark, use_container_width=True)
        else:
            st.info("No sparkline data available.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: sparklines failed: %s", exc, exc_info=True)
