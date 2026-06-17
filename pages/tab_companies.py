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
    Tries live yfinance first; always falls back to static synthetic data
    when live data is empty or unavailable.
    """
    try:
        from utils.data import fetch_all_history
        hist = fetch_all_history()
        if hist and len(hist) >= 10:  # meaningful live data
            return hist, True
    except OSError as exc:
        log.warning("tab_companies: network error fetching history: %s", exc)
    except Exception as exc:  # noqa: BLE001
        log.warning("tab_companies: fetch_all_history failed: %s", exc)
    log.info("tab_companies: using static synthetic history fallback")
    return _build_static_history(), False


def _build_pie_from_history(history: dict, title: str) -> object:
    """Build sector pie directly from a history dict (works without live price rows)."""
    rows = []
    for s in NIFTY50:
        h = history.get(s["symbol"])
        if h is not None and not h.empty and "Close" in h.columns:
            price = float(h["Close"].dropna().iloc[-1])
        else:
            price = 0.0
        rows.append({"Sector": s["sector"], "_curr": price})
    return build_sector_pie(pd.DataFrame(rows), title=title)


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
    with st.spinner("Loading stock data…"):
        try:
            df_rows = build_stock_rows_cached()
        except Exception as exc:  # noqa: BLE001
            log.error("tab_companies: build_stock_rows_cached failed: %s", exc, exc_info=True)
            st.error("Could not load stock data.")
            return

    df_filtered = df_rows[df_rows["Sector"] == sel_sec] if sel_sec != "All" else df_rows

    display_df = _sanitize_numeric_cols(
        df_filtered.drop(columns=["_curr", "_pct"], errors="ignore")
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    export_buttons(
        display_df,
        filename_stem=f"nifty50_{'all' if sel_sec == 'All' else sel_sec.replace(' ', '_')}",
        title=f"Nifty 50 Companies — {sel_sec}",
        key_suffix="companies",
    )

    divider()

    # ── Fetch history ONCE — used by ALL three charts below ───────────────────
    with st.spinner("Loading price history…"):
        all_hist, is_live = _get_history()

    if not is_live:
        st.info(
            "⚠️ Live market history is unavailable right now. "
            "The charts below use representative synthetic data seeded from "
            "current Nifty 50 prices so you can explore all dashboards."
        )

    # Narrow history to selected sector if needed
    if sel_sec != "All":
        sector_syms  = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
        sector_names = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
    else:
        sector_syms  = SYMBOLS
        sector_names = [s["name"] for s in NIFTY50]

    # ── Sector Allocation Pie ─────────────────────────────────────────────────
    sec("Sector Allocation")
    st.caption(
        "Donut chart weighted by current price sum per sector — "
        + ("live data" if is_live else "representative data (market closed / offline)")
    )
    try:
        pie_title = (
            "Sector Allocation — Nifty 50"
            if sel_sec == "All"
            else f"Sector Allocation — {sel_sec} highlighted"
        )
        fig_pie = _build_pie_from_history(all_hist, pie_title)
        if fig_pie.data:
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("⚠️ Could not render sector pie — no price data available.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: sector pie failed: %s", exc, exc_info=True)
        st.warning("Sector Allocation chart could not be rendered.")

    divider()

    # ── 1-Day % Change bar ────────────────────────────────────────────────────
    if "_pct" in df_filtered.columns:
        valid = df_filtered[df_filtered["_pct"].notna()].copy()
        if not valid.empty:
            try:
                title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
                fig = build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:  # noqa: BLE001
                log.error("tab_companies: bar chart failed: %s", exc, exc_info=True)

    divider()

    # ── Correlation heatmap ───────────────────────────────────────────────────
    sec("30-Day Return Correlation Heatmap")
    st.caption(
        "Pairwise Pearson correlations of daily returns over the last 30 trading sessions. "
        "Blue\u00a0=\u00a0negative, red\u00a0=\u00a0positive."
    )
    try:
        hm_height = max(400, min(700, len(sector_syms) * 14 + 120))
        fig_hm = build_correlation_heatmap(
            all_hist, sector_syms, sector_names,
            title=f"30-Day Correlation — {sel_sec}",
            height=hm_height,
        )
        if fig_hm.data:
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Not enough overlapping data to compute correlations.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: heatmap render failed: %s", exc, exc_info=True)

    divider()

    # ── 20-Day Sparklines ─────────────────────────────────────────────────────
    sec("20-Day Price Sparklines")
    st.caption(
        "Each mini-chart shows the last 20 trading sessions. "
        "Green\u00a0=\u00a0net gain, red\u00a0=\u00a0net loss."
    )
    try:
        spark_height = max(300, (len(sector_syms) // 5 + 1) * 110)
        fig_spark = build_sparkline_table(
            all_hist, sector_syms, sector_names,
            height=spark_height,
        )
        if fig_spark.data:
            st.plotly_chart(fig_spark, use_container_width=True)
        else:
            st.info("No sparkline data available.")
    except Exception as exc:  # noqa: BLE001
        log.error("tab_companies: sparklines failed: %s", exc, exc_info=True)
