"""Tab 2 — All 50 Companies."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

from utils.logger import get_logger
from utils.constants import NIFTY50, SYMBOLS
from utils.charts import build_pct_bar, build_sector_pie
from utils.export import export_buttons

log = get_logger(__name__)

_PURE_NUM = r"^[\-+]?[\d,\.]+$"


# ---------------------------------------------------------------------------
# Build guaranteed static history inline — no imports from charts.py
# ---------------------------------------------------------------------------

def _make_static_hist() -> dict[str, pd.DataFrame]:
    SEEDS = {
        "RELIANCE.NS": 1480,   "HDFCBANK.NS": 1920,  "ICICIBANK.NS": 1340,
        "INFY.NS": 1780,       "TCS.NS": 4050,        "BHARTIARTL.NS": 1850,
        "ITC.NS": 480,         "KOTAKBANK.NS": 1890,  "LT.NS": 3580,
        "HCLTECH.NS": 1920,    "AXISBANK.NS": 1245,   "SBIN.NS": 820,
        "BAJFINANCE.NS": 7200, "WIPRO.NS": 580,       "ASIANPAINT.NS": 2380,
        "MARUTI.NS": 12800,    "SUNPHARMA.NS": 1720,  "TITAN.NS": 3540,
        "ULTRACEMCO.NS": 11500,"ONGC.NS": 275,        "NTPC.NS": 365,
        "POWERGRID.NS": 315,   "M&M.NS": 3150,        "TATAMOTORS.NS": 925,
        "TATASTEEL.NS": 165,   "JSWSTEEL.NS": 980,    "HINDALCO.NS": 690,
        "ADANIENT.NS": 2980,   "ADANIPORTS.NS": 1380, "BAJAJFINSV.NS": 1980,
        "BAJAJAUTO.NS": 9800,  "HEROMOTOCO.NS": 4750, "CIPLA.NS": 1540,
        "DRREDDY.NS": 6450,    "DIVISLAB.NS": 5200,   "EICHERMOT.NS": 5500,
        "GRASIM.NS": 2750,     "HDFCLIFE.NS": 780,    "SBILIFE.NS": 1650,
        "INDUSINDBK.NS": 980,  "TATACONSUM.NS": 1020, "BRITANNIA.NS": 4800,
        "NESTLEIND.NS": 2250,  "HINDUNILVR.NS": 2380, "COALINDIA.NS": 415,
        "BPCL.NS": 320,        "TECHM.NS": 1580,      "LTF.NS": 195,
        "SHRIRAMFIN.NS": 3250, "BEL.NS": 285,
    }
    VOLS = {s: 0.014 for s in SEEDS}
    VOLS.update({"BAJFINANCE.NS": 0.018, "TATASTEEL.NS": 0.020, "ADANIENT.NS": 0.022})

    out: dict[str, pd.DataFrame] = {}
    dates = pd.bdate_range(end="2026-06-17", periods=35)
    n = len(dates)

    for sym, base in SEEDS.items():
        seed = int(hashlib.md5(sym.encode()).hexdigest()[:8], 16) % (2 ** 31)
        rng = np.random.default_rng(seed)
        vol = VOLS.get(sym, 0.014)

        rets = rng.normal(0.0002, vol, n)
        closes = np.zeros(n, dtype=float)
        closes[-1] = float(base)
        for i in range(n - 2, -1, -1):
            closes[i] = closes[i + 1] / (1.0 + rets[i + 1])

        sp = closes * vol * 0.8
        opens  = closes + rng.uniform(-sp * 0.5, sp * 0.5)
        highs  = np.maximum(opens, closes) + np.abs(rng.normal(0, sp * 0.5))
        lows   = np.minimum(opens, closes) - np.abs(rng.normal(0, sp * 0.5))
        vols   = rng.integers(500_000, 5_000_000, n).astype(float)

        out[sym] = pd.DataFrame(
            {"Open": opens.astype(float),
             "High": highs.astype(float),
             "Low":  lows.astype(float),
             "Close": closes.astype(float),
             "Volume": vols},
            index=dates,
        )
    return out


# Build ONCE at module load — zero network calls
_HIST: dict[str, pd.DataFrame] = _make_static_hist()


# ---------------------------------------------------------------------------
# Inline heatmap builder
# ---------------------------------------------------------------------------

def _render_heatmap(syms: list[str], names: list[str], title: str) -> None:
    """Build and render the correlation heatmap directly — no function call."""
    labels = [s.replace(".NS", "") for s in syms]

    # Build price DataFrame from static history
    price_data: dict[str, list[float]] = {}
    for sym, lbl in zip(syms, labels):
        h = _HIST.get(sym)
        if h is None or h.empty:
            continue
        vals = list(h["Close"].astype(float))
        if len(vals) >= 5:
            price_data[lbl] = vals

    if len(price_data) < 2:
        st.warning("Not enough data for heatmap.")
        return

    # Build correlation matrix manually — no pandas corr(), pure numpy
    lbls = list(price_data.keys())
    mat = np.array([price_data[l] for l in lbls], dtype=float)  # shape: (n_stocks, n_days)

    # Daily returns
    rets = np.diff(mat, axis=1) / mat[:, :-1]  # shape: (n_stocks, n_days-1)
    rets = rets[:, -30:]  # last 30

    n = len(lbls)
    corr = np.ones((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            r = np.corrcoef(rets[i], rets[j])[0, 1]
            v = 0.0 if np.isnan(r) else float(r)
            corr[i, j] = v
            corr[j, i] = v

    text = [[f"{corr[i,j]:.2f}" for j in range(n)] for i in range(n)]

    height = max(420, min(700, n * 14 + 120))
    fig = go.Figure(go.Heatmap(
        z=corr.tolist(),
        x=lbls,
        y=lbls,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=9),
        colorscale="RdBu",
        zmid=0, zmin=-1, zmax=1,
        hovertemplate="%{y} ↔ %{x}: <b>%{z:.3f}</b><extra></extra>",
        colorbar=dict(title="r", thickness=12, len=0.8),
    ))
    fig.update_layout(
        title=title,
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
        margin=dict(t=60, b=120, l=80, r=60),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Inline sparkline builder
# ---------------------------------------------------------------------------

def _render_sparklines(syms: list[str], names: list[str]) -> None:
    """Build and render sparklines directly — no function call."""
    labels = [s.replace(".NS", "") for s in syms]

    valid: list[tuple[str, str, list[float]]] = []
    for sym, lbl in zip(syms, labels):
        h = _HIST.get(sym)
        if h is None or h.empty:
            continue
        vals = h["Close"].astype(float).tolist()[-20:]
        if len(vals) >= 2:
            valid.append((sym, lbl, vals))

    if not valid:
        st.warning("No sparkline data available.")
        return

    COLS = 5
    ROWS = (len(valid) + COLS - 1) // COLS
    height = max(300, ROWS * 110)

    fig = make_subplots(
        rows=ROWS, cols=COLS,
        horizontal_spacing=0.04,
        vertical_spacing=0.08,
    )

    for idx, (sym, lbl, vals) in enumerate(valid):
        row = idx // COLS + 1
        col = idx % COLS + 1
        pct = (vals[-1] - vals[0]) / vals[0] * 100 if vals[0] != 0 else 0.0
        colour = "#10b981" if pct >= 0 else "#ef4444"
        x_vals = list(range(len(vals)))

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=vals,
                mode="lines",
                line=dict(color=colour, width=1.5),
                name=lbl,
                showlegend=False,
                hovertemplate=f"<b>{lbl}</b><br>₹%{{y:,.2f}}<extra></extra>",
            ),
            row=row, col=col,
        )
        fig.update_xaxes(showticklabels=False, showgrid=False, row=row, col=col)
        fig.update_yaxes(showticklabels=False, showgrid=False, row=row, col=col)
        fig.add_annotation(
            text=f"<b>{lbl}</b> {pct:+.1f}%",
            xref="paper", yref="paper",
            x=(col - 0.5) / COLS,
            y=1.0 - (row - 1) / ROWS + 0.005,
            showarrow=False,
            font=dict(size=9, color=colour),
            xanchor="center",
        )

    fig.update_layout(
        title=f"20-Day Price Sparklines ({len(valid)} stocks)",
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        margin=dict(t=80, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_numeric_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype != object:
            continue
        non_null = df[col].dropna()
        if non_null.empty or df[col].isna().mean() > 0.05:
            continue
        if not non_null.astype(str).str.match(_PURE_NUM).all():
            continue
        try:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False), errors="raise"
            )
        except Exception:
            pass
    return df


def _build_pie_rows() -> pd.DataFrame:
    rows = []
    for s in NIFTY50:
        h = _HIST.get(s["symbol"])
        price = float(h["Close"].iloc[-1]) if (h is not None and not h.empty) else 1000.0
        rows.append({"Sector": s["sector"], "_curr": price, "Symbol": s["symbol"]})
    return pd.DataFrame(rows)


def _render_dashboard_metrics() -> None:
    gains, losses, vols_list = [], [], []
    for s in NIFTY50:
        h = _HIST.get(s["symbol"])
        if h is None or h.empty:
            continue
        closes = h["Close"].astype(float).tail(30)
        if len(closes) < 2:
            continue
        ret = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
        vol = closes.pct_change().dropna().std() * 100
        gains.append((ret, s["name"]))
        losses.append((ret, s["name"]))
        vols_list.append((vol, s["name"]))

    if not gains:
        return
    gains.sort(reverse=True)
    losses.sort()
    vols_list.sort(reverse=True)
    avg = sum(g[0] for g in gains) / len(gains)

    st.markdown("### 📊 Quick Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🚀 Top Gainer (30D)",  gains[0][1],  f"{gains[0][0]:+.1f}%")
    c2.metric("📉 Top Loser (30D)",   losses[0][1], f"{losses[0][0]:+.1f}%")
    c3.metric("⚡ Most Volatile",      vols_list[0][1], f"σ {vols_list[0][0]:.2f}%/day")
    c4.metric("📈 Avg 30D Return",    "Nifty 50",   f"{avg:+.1f}%")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

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

    if not market_open:
        st.info(
            "⚠️ Market is closed — charts below use last-session closing prices and work 24/7."
        )

    _render_dashboard_metrics()
    divider()

    sectors = ["All"] + sorted({s["sector"] for s in NIFTY50})
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")

    # Stock table
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

    if sel_sec != "All":
        sector_syms  = [s["symbol"] for s in NIFTY50 if s["sector"] == sel_sec]
        sector_names = [s["name"]   for s in NIFTY50 if s["sector"] == sel_sec]
    else:
        sector_syms  = SYMBOLS
        sector_names = [s["name"] for s in NIFTY50]

    # Sector Pie
    sec("Sector Allocation")
    st.caption("Donut chart weighted by latest Close price per sector.")
    try:
        fig_pie = build_sector_pie(
            _build_pie_rows(),
            "Sector Allocation — Nifty 50" if sel_sec == "All" else f"Sector Allocation — {sel_sec}",
        )
        if fig_pie.data:
            st.plotly_chart(fig_pie, use_container_width=True)
    except Exception as exc:
        log.error("sector pie: %s", exc, exc_info=True)
    divider()

    # 1-Day % Change bar
    if "_pct" in df_filtered.columns:
        valid = df_filtered[df_filtered["_pct"].notna()].copy()
        if not valid.empty:
            try:
                fig = build_pct_bar(
                    valid, "Symbol", "_pct",
                    "1-Day % Change" if market_open else "1-Day % Change (last session)",
                    text_col="Change (%)",
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                log.error("bar chart: %s", exc, exc_info=True)
    divider()

    # Heatmap — fully inline, no external function
    sec("30-Day Return Correlation Heatmap")
    st.caption(
        "Pairwise Pearson correlations of daily returns over the last 30 trading sessions. "
        "Blue\u00a0= negative, red\u00a0= positive."
    )
    _render_heatmap(
        sector_syms, sector_names,
        f"30-Day Correlation — {sel_sec}",
    )
    divider()

    # Sparklines — fully inline, no external function
    sec("20-Day Price Sparklines")
    st.caption(
        "Each mini-chart shows the last 20 trading sessions. "
        "Green\u00a0= net gain, red\u00a0= net loss."
    )
    _render_sparklines(sector_syms, sector_names)
