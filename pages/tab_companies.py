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

# ---------------------------------------------------------------------------
# Module-level static history — built ONCE, reused for every render call.
# This is the guaranteed 24/7 data source for Heatmap + Sparklines.
# No network calls, no yfinance, no cache TTL dependencies.
# ---------------------------------------------------------------------------
try:
    _STATIC_HIST: dict = _build_static_history()
    log.info("tab_companies: static history ready (%d symbols)", len(_STATIC_HIST))
except Exception as _e:
    log.error("tab_companies: _build_static_history failed at import: %s", _e)
    _STATIC_HIST = {}


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


def _get_hist() -> dict:
    """Return the module-level static history, rebuilding if somehow empty."""
    global _STATIC_HIST
    if not _STATIC_HIST:
        _STATIC_HIST = _build_static_history()
    return _STATIC_HIST


def _build_pie_rows() -> pd.DataFrame:
    """Build sector rows using static history prices."""
    hist = _get_hist()
    rows = []
    for s in NIFTY50:
        h = hist.get(s["symbol"])
        if h is not None and not h.empty and "Close" in h.columns:
            closes = h["Close"].dropna()
            price = float(closes.iloc[-1]) if not closes.empty else 1000.0
        else:
            price = 1000.0
        rows.append({"Sector": s["sector"], "_curr": price, "Symbol": s["symbol"]})
    return pd.DataFrame(rows)


def _render_dashboard_metrics() -> None:
    """4 KPI metric cards using static history."""
    try:
        hist = _get_hist()
        gains, losses, vols = [], [], []
        for s in NIFTY50:
            h = hist.get(s["symbol"])
            if h is None or h.empty or "Close" not in h.columns:
                continue
            closes = h["Close"].dropna().tail(30)
            if len(closes) < 2:
                continue
            ret = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
            vol = h["Close"].dropna().pct_change().dropna().std() * 100
            gains.append((ret, s["name"]))
            losses.append((ret, s["name"]))
            vols.append((vol, s["name"]))

        if not gains:
            return
        gains.sort(reverse=True)
        losses.sort()
        vols.sort(reverse=True)
        avg = sum(g[0] for g in gains) / len(gains)

        st.markdown("### 📊 Quick Dashboard")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🚀 Top Gainer (30D)",  gains[0][1],  f"{gains[0][0]:+.1f}%")
        c2.metric("📉 Top Loser (30D)",   losses[0][1], f"{losses[0][0]:+.1f}%")
        c3.metric("⚡ Most Volatile",      vols[0][1],   f"σ {vols[0][0]:.2f}%/day")
        c4.metric("📈 Avg 30D Return",    "Nifty 50",   f"{avg:+.1f}%")
    except Exception as exc:
        log.warning("dashboard metrics: %s", exc)


def render(
    market_open: bool,
    market_status: str,
    last_close_label: str,
    build_stock_rows_cached,
) -> None:
    from utils.app_helpers import hero, closed_banner, sec, divider

    hero(
        "All 50 Companies",
        "Live prices" if market_open else "Last closing prices",
    )
    closed_banner(market_open, market_status, last_close_label)

    # Always show static-backed note when market closed
    if not market_open:
        st.info(
            "⚠️ Market is closed — all charts below are built from the most recent "
            "session’s closing prices and are fully functional 24/7."
        )

    # ── Quick Dashboard (always works — static data) ─────────────────────
    _render_dashboard_metrics()
    divider()

    sectors = ["All"] + sorted({s["sector"] for s in NIFTY50})
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")

    # ── Stock data table ─────────────────────────────────────────────
    with st.spinner("Loading stock data…"):
        try:
            df_rows = build_stock_rows_cached()
        except Exception as exc:
            log.error("build_stock_rows_cached: %s", exc, exc_info=True)
            st.error("Could not load stock data.")
            return

    df_filtered = df_rows[df_rows["Sector"] == sel_sec] if sel_sec != "All" else df_rows
    display_df  = _sanitize_numeric_cols(
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

    # Sector symbol/name lists
    if sel_sec != "All":
        sector_syms  = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
        sector_names = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
    else:
        sector_syms  = SYMBOLS
        sector_names = [s["name"] for s in NIFTY50]

    # Guaranteed history for charts
    hist = _get_hist()

    # ── Sector Allocation Pie ──────────────────────────────────────────
    sec("Sector Allocation")
    st.caption("Donut chart weighted by latest Close price per sector.")
    try:
        pie_rows = _build_pie_rows()
        fig_pie  = build_sector_pie(
            pie_rows,
            "Sector Allocation — Nifty 50" if sel_sec == "All"
            else f"Sector Allocation — {sel_sec}",
        )
        if fig_pie.data:
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("⚠️ Sector pie could not be rendered.")
    except Exception as exc:
        log.error("sector pie: %s", exc, exc_info=True)
    divider()

    # ── 1-Day % Change bar (live data when available) ───────────────────
    if "_pct" in df_filtered.columns:
        valid = df_filtered[df_filtered["_pct"].notna()].copy()
        if not valid.empty:
            try:
                title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
                fig = build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                log.error("bar chart: %s", exc, exc_info=True)
    divider()

    # ── 30-Day Return Correlation Heatmap (STATIC — always renders) ───────
    sec("30-Day Return Correlation Heatmap")
    st.caption(
        "Pairwise Pearson correlations of daily returns over the last 30 trading sessions. "
        "Blue\u00a0=\u00a0negative, red\u00a0=\u00a0positive."
    )
    try:
        hm_height = max(400, min(700, len(sector_syms) * 14 + 120))
        fig_hm = build_correlation_heatmap(
            hist, sector_syms, sector_names,
            title=f"30-Day Correlation — {sel_sec}",
            height=hm_height,
        )
        if fig_hm.data:
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            # Should never happen with static data — log for diagnosis
            log.error(
                "heatmap returned empty figure! hist keys=%d sector_syms=%s",
                len(hist), sector_syms[:3],
            )
            st.warning("⚠️ Heatmap could not be rendered.")
    except Exception as exc:
        log.error("heatmap: %s", exc, exc_info=True)
    divider()

    # ── 20-Day Price Sparklines (STATIC — always renders) ───────────────
    sec("20-Day Price Sparklines")
    st.caption(
        "Each mini-chart shows the last 20 trading sessions. "
        "Green\u00a0=\u00a0net gain, red\u00a0=\u00a0net loss."
    )
    try:
        spark_height = max(300, (len(sector_syms) // 5 + 1) * 110)
        fig_spark = build_sparkline_table(
            hist, sector_syms, sector_names,
            height=spark_height,
        )
        if fig_spark.data:
            st.plotly_chart(fig_spark, use_container_width=True)
        else:
            log.error(
                "sparklines returned empty figure! hist keys=%d sector_syms=%s",
                len(hist), sector_syms[:3],
            )
            st.warning("⚠️ Sparklines could not be rendered.")
    except Exception as exc:
        log.error("sparklines: %s", exc, exc_info=True)
