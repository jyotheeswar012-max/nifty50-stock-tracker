"""Tab 0 — Market Overview.

This module is imported by app.py; it is NOT a standalone Streamlit page.
Streamlit discovers it as a page only if it's in pages/ without a _ prefix,
which is why we keep a _tab_overview.py stub there instead.
"""
from __future__ import annotations

import streamlit as st
from utils.logger import get_logger
from utils.constants import NIFTY50
from utils.data import fetch_all_stocks_5d, fetch_ticker
from utils.calculations import safe_float

log = get_logger(__name__)


def render(market_open: bool, market_status: str, last_close_label: str) -> None:
    from utils.app_helpers import hero, closed_banner, sec, divider

    hero("🏦 Market Overview", "Nifty 50 at a glance")
    closed_banner(market_open, market_status, last_close_label)

    try:
        _render_index_kpis(market_open)
    except Exception as exc:
        log.error("tab_overview: index KPIs failed: %s", exc, exc_info=True)
        st.warning("Index data temporarily unavailable.")

    divider()

    try:
        _render_sector_heatmap()
    except Exception as exc:
        log.error("tab_overview: sector heatmap failed: %s", exc, exc_info=True)
        st.info("Sector breakdown unavailable.")


def _render_index_kpis(market_open: bool) -> None:
    import pandas as pd
    from utils.charts import build_price_chart

    nifty_sym = "^NSEI"
    with st.spinner("Loading Nifty 50 index…"):
        df = fetch_ticker(nifty_sym, "1mo")

    if df.empty or "Close" not in df.columns:
        st.warning("⚠️ Nifty 50 index data unavailable right now.")
        return

    close   = safe_float(df["Close"].iloc[-1])
    prev    = safe_float(df["Close"].iloc[-2]) if len(df) > 1 else close
    chg     = close - prev
    pct     = (chg / prev * 100) if prev else 0.0
    hi52    = safe_float(df["High"].max())
    lo52    = safe_float(df["Low"].min())
    vol_avg = int(df["Volume"].mean()) if "Volume" in df.columns else 0

    lbl = "Live Price" if market_open else "Last Close"
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(lbl, f"₹{close:,.2f}")
    c2.metric("Change", f"{chg:+.2f}", delta=f"{pct:+.2f}%")
    c3.metric("1M High", f"₹{hi52:,.2f}")
    c4.metric("1M Low",  f"₹{lo52:,.2f}")
    c5.metric("Avg Volume", f"{vol_avg:,}")

    st.markdown("### Nifty 50 — 1 Month Trend")
    try:
        fig = build_price_chart(df, "Nifty 50", "1mo", "Line", height=320)
        fig.update_layout(autosize=True)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        log.warning("tab_overview: Nifty chart failed: %s", exc)
        st.line_chart(df["Close"])


def _render_sector_heatmap() -> None:
    import pandas as pd
    import plotly.graph_objects as go

    st.markdown("### Sector Breakdown")
    with st.spinner("Loading sector data…"):
        stock_data = fetch_all_stocks_5d()

    sector_map: dict[str, list[float]] = {}
    for s in NIFTY50:
        sym    = s["symbol"]
        sector = s["sector"]
        df     = stock_data.get(sym)
        if df is None or df.empty or "Close" not in df.columns:
            continue
        closes = df["Close"].dropna()
        if len(closes) < 2:
            continue
        pct = (safe_float(closes.iloc[-1]) - safe_float(closes.iloc[-2]))
        pct = pct / safe_float(closes.iloc[-2]) * 100 if safe_float(closes.iloc[-2]) else 0.0
        sector_map.setdefault(sector, []).append(pct)

    if not sector_map:
        st.info("Sector data not available.")
        return

    rows = [
        {"Sector": sec, "Avg Change (%)": round(sum(v) / len(v), 2), "Stocks": len(v)}
        for sec, v in sorted(sector_map.items(), key=lambda x: -sum(x[1]) / len(x[1]))
    ]
    df_sec = pd.DataFrame(rows)

    colors = [
        "#22c55e" if x > 0 else ("#f97316" if x == 0 else "#ef4444")
        for x in df_sec["Avg Change (%)"]
    ]
    fig = go.Figure(go.Bar(
        x=df_sec["Sector"],
        y=df_sec["Avg Change (%)"],
        marker_color=colors,
        text=[f"{v:+.2f}%" for v in df_sec["Avg Change (%)"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        title="Sector Avg % Change (Last Session)",
        xaxis_title="Sector",
        yaxis_title="Avg Change (%)",
        plot_bgcolor="#0f172a",
        paper_bgcolor="#0f172a",
        font_color="#e2e8f0",
        height=380,
        margin=dict(t=50, b=80, l=40, r=20),
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#64748b", line_width=1)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_sec, use_container_width=True, hide_index=True)
