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


def _normalise_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure DataFrame has a 'Close' column regardless of yfinance column naming.
    Handles: 'Adj Close', 'adj close', MultiIndex leftovers.
    """
    if df is None or df.empty:
        return df
    cols = {c.lower(): c for c in df.columns}
    if "close" not in cols:
        # Try Adj Close → Close
        for candidate in ("adj close", "adjclose", "adjusted close"):
            if candidate in cols:
                df = df.copy()
                df["Close"] = df[cols[candidate]]
                log.info("_normalise_df: renamed '%s' -> 'Close'", cols[candidate])
                break
    return df


def _is_usable(df) -> bool:
    """True if df has Close column with >= 5 non-NaN values."""
    if df is None or not hasattr(df, "empty") or df.empty:
        return False
    if "Close" not in df.columns:
        return False
    return df["Close"].dropna().__len__() >= 5


def _fetch_live_history_2mo() -> dict:
    """Fetch 2-month daily bars for all 50 symbols — enough for 30-day heatmap.
    Uses a dedicated lightweight yfinance batch (not the heavy 5y fetch_all_history).
    Returns {} on any failure.
    """
    try:
        import yfinance as yf
        import time
        log.info("tab_companies: fetching 2mo history batch")
        raw = yf.download(
            tickers=SYMBOLS,
            period="2mo",
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True,
            timeout=25,
        )
        if raw is None or raw.empty:
            log.warning("tab_companies: yf 2mo batch returned empty")
            return {}

        result = {}
        for sym in SYMBOLS:
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    try:
                        df = raw.xs(sym, axis=1, level=1).copy()
                    except KeyError:
                        short = sym.replace(".NS", "")
                        df = raw.xs(short, axis=1, level=1).copy()
                else:
                    df = raw.copy()

                # Strip timezone, normalize index
                if hasattr(df.index, "tz") and df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                df.index = pd.to_datetime(df.index).normalize()
                df = _normalise_df(df)

                if _is_usable(df):
                    result[sym] = df
            except Exception as exc:
                log.debug("tab_companies: 2mo extract failed for %s: %s", sym, exc)

        log.info("tab_companies: 2mo batch got %d/%d symbols", len(result), len(SYMBOLS))
        return result
    except Exception as exc:
        log.warning("tab_companies: 2mo batch failed: %s", exc)
        return {}


def _get_history() -> tuple[dict, bool]:
    """Return (history_dict, is_live).
    Strategy:
      1. Try dedicated 2mo yfinance batch (fast, market-open or closed)
      2. Try fetch_all_history() (5y, already cached with TTL=3600)
      3. ALWAYS fall back to deterministic static data
    Any returned live dict is patched to ensure every symbol has a 'Close' column.
    """
    # --- Attempt 1: dedicated 2mo batch ---
    hist_2mo = _fetch_live_history_2mo()
    usable_count = sum(1 for df in hist_2mo.values() if _is_usable(df))
    if usable_count >= 10:
        log.info("tab_companies: using 2mo live history (%d usable symbols)", usable_count)
        return hist_2mo, True

    # --- Attempt 2: fetch_all_history (5y, TTL-cached) ---
    try:
        from utils.data import fetch_all_history
        hist_5y = fetch_all_history()
        # Patch missing Close columns
        for sym in list(hist_5y.keys()):
            hist_5y[sym] = _normalise_df(hist_5y[sym])
        usable_5y = sum(1 for df in hist_5y.values() if _is_usable(df))
        if usable_5y >= 10:
            log.info("tab_companies: using cached 5y history (%d usable symbols)", usable_5y)
            return hist_5y, True
        log.warning("tab_companies: 5y history only %d usable symbols", usable_5y)
    except Exception as exc:
        log.warning("tab_companies: fetch_all_history failed: %s", exc)

    # --- Guaranteed static fallback ---
    log.info("tab_companies: using static synthetic history")
    static = _build_static_history()
    return static, False


def _build_pie_from_history(history: dict, title: str) -> object:
    """Build sector pie from last Close price per symbol."""
    rows = []
    for s in NIFTY50:
        h = history.get(s["symbol"])
        h = _normalise_df(h) if h is not None else None
        if _is_usable(h):
            price = float(h["Close"].dropna().iloc[-1])
        else:
            price = 1000.0
        rows.append({"Sector": s["sector"], "_curr": price})
    return build_sector_pie(pd.DataFrame(rows), title=title)


def _render_dashboard_metrics(all_hist: dict) -> None:
    """4 KPI cards: Top Gainer, Top Loser, Most Volatile, Avg 30D Return."""
    try:
        gains, losses, vols = [], [], []
        for s in NIFTY50:
            sym = s["symbol"]
            h = _normalise_df(all_hist.get(sym))
            if not _is_usable(h):
                continue
            closes = h["Close"].dropna()
            if len(closes) < 2:
                continue
            # Use last 30 rows (trading days) if available
            closes_30 = closes.tail(30)
            ret_pct = (closes_30.iloc[-1] / closes_30.iloc[0] - 1) * 100
            daily_std = closes.pct_change().dropna().std() * 100
            name = s["name"]
            gains.append((ret_pct, name))
            losses.append((ret_pct, name))
            vols.append((daily_std, name))

        if not gains:
            return

        gains.sort(reverse=True)
        losses.sort()
        vols.sort(reverse=True)
        avg_ret = sum(g[0] for g in gains) / len(gains)

        st.markdown("### 📊 Quick Dashboard")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🚀 Top Gainer (30D)",  gains[0][1],  f"{gains[0][0]:+.1f}%")
        c2.metric("📉 Top Loser (30D)",   losses[0][1], f"{losses[0][0]:+.1f}%")
        c3.metric("⚡ Most Volatile",      vols[0][1],   f"σ {vols[0][0]:.2f}%/day")
        c4.metric("📈 Avg 30D Return",    "Nifty 50",   f"{avg_ret:+.1f}%")
    except Exception as exc:
        log.warning("tab_companies: dashboard metrics failed: %s", exc)


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

    # ── Fetch history EARLY ────────────────────────────────────────────────
    with st.spinner("Loading price history…"):
        all_hist, is_live = _get_history()

    # Absolute last resort
    if not all_hist:
        log.error("tab_companies: all_hist empty — forcing static")
        all_hist = _build_static_history()
        is_live = False

    data_label = "live data" if is_live else "last available / representative data"
    if not is_live:
        st.info(
            "⚠️ Market closed or data unavailable — "
            "charts are built from the most recent cached prices. "
            "All dashboards are fully functional."
        )

    # ── Quick Dashboard KPIs ───────────────────────────────────────────────
    _render_dashboard_metrics(all_hist)
    divider()

    sectors = ["All"] + sorted({s["sector"] for s in NIFTY50})
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")

    # ── Stock data table ───────────────────────────────────────────────────
    with st.spinner("Loading stock data…"):
        try:
            df_rows = build_stock_rows_cached()
        except Exception as exc:
            log.error("tab_companies: build_stock_rows_cached failed: %s", exc, exc_info=True)
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

    # Sector symbol/name lists for charts
    if sel_sec != "All":
        sector_syms  = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
        sector_names = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
    else:
        sector_syms  = SYMBOLS
        sector_names = [s["name"] for s in NIFTY50]

    # ── Sector Allocation Pie ──────────────────────────────────────────────
    sec("Sector Allocation")
    st.caption(f"Donut chart weighted by latest Close price sum per sector — {data_label}")
    try:
        fig_pie = _build_pie_from_history(
            all_hist,
            "Sector Allocation — Nifty 50" if sel_sec == "All"
            else f"Sector Allocation — {sel_sec} highlighted",
        )
        if fig_pie.data:
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("⚠️ Could not render sector pie.")
    except Exception as exc:
        log.error("tab_companies: sector pie failed: %s", exc, exc_info=True)
    divider()

    # ── 1-Day % Change bar ─────────────────────────────────────────────────
    if "_pct" in df_filtered.columns:
        valid = df_filtered[df_filtered["_pct"].notna()].copy()
        if not valid.empty:
            try:
                title = "1-Day % Change" if market_open else "1-Day % Change (last session)"
                fig = build_pct_bar(valid, "Symbol", "_pct", title, text_col="Change (%)")
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                log.error("tab_companies: bar chart failed: %s", exc, exc_info=True)
    divider()

    # ── 30-Day Return Correlation Heatmap ──────────────────────────────────
    sec("30-Day Return Correlation Heatmap")
    st.caption(
        "Pairwise Pearson correlations of daily returns over the last 30 trading sessions. "
        "Blue\u00a0=\u00a0negative, red\u00a0=\u00a0positive. " + data_label + "."
    )
    # Patch all sector symbols to ensure Close column exists
    for sym in sector_syms:
        if sym in all_hist:
            all_hist[sym] = _normalise_df(all_hist[sym])
    present = [s for s in sector_syms if _is_usable(all_hist.get(s))]
    log.info("tab_companies: heatmap — %d/%d symbols usable", len(present), len(sector_syms))
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
            st.warning("⚠️ Not enough data to compute correlations — try selecting 'All' sectors.")
    except Exception as exc:
        log.error("tab_companies: heatmap render failed: %s", exc, exc_info=True)
    divider()

    # ── 20-Day Price Sparklines ────────────────────────────────────────────
    sec("20-Day Price Sparklines")
    st.caption(
        "Each mini-chart shows the last 20 trading sessions. "
        "Green\u00a0=\u00a0net gain, red\u00a0=\u00a0net loss. " + data_label + "."
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
            st.warning("⚠️ No sparkline data available.")
    except Exception as exc:
        log.error("tab_companies: sparklines failed: %s", exc, exc_info=True)
