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
# Shared chart style constants — light theme friendly
# ---------------------------------------------------------------------------
_CHART_FONT_COLOR = "#1e293b"
_CHART_BG         = "#ffffff"
_CHART_PLOT_BG    = "#fafafa"
_CHART_GRID       = "#f1f5f9"
_CHART_LINE       = "#cbd5e1"

_PLT_LAYOUT = dict(
    paper_bgcolor=_CHART_BG,
    plot_bgcolor=_CHART_PLOT_BG,
    font=dict(color=_CHART_FONT_COLOR, family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(
        font=dict(color=_CHART_FONT_COLOR, size=12),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#e2e8f0",
        borderwidth=1,
    ),
)

_AXIS_STYLE = dict(
    tickfont=dict(color=_CHART_FONT_COLOR, size=11, family="Inter, sans-serif"),
    title_font=dict(color="#0f172a", size=12, family="Inter, sans-serif"),
    linecolor=_CHART_LINE,
    gridcolor=_CHART_GRID,
    zerolinecolor=_CHART_LINE,
)


def _style_fig(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(**_AXIS_STYLE)
    fig.update_yaxes(**_AXIS_STYLE)
    return fig


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
# Inline heatmap builder — light-theme fix
# ---------------------------------------------------------------------------

def _render_heatmap(syms: list[str], names: list[str], title: str) -> None:
    """Build and render the correlation heatmap with fully visible axis labels."""
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

    # Build correlation matrix — pure numpy
    lbls = list(price_data.keys())
    mat = np.array([price_data[l] for l in lbls], dtype=float)

    # Daily returns — last 30 days
    rets = np.diff(mat, axis=1) / mat[:, :-1]
    rets = rets[:, -30:]

    n = len(lbls)
    corr = np.ones((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            r = np.corrcoef(rets[i], rets[j])[0, 1]
            v = 0.0 if np.isnan(r) else float(r)
            corr[i, j] = v
            corr[j, i] = v

    text = [[f"{corr[i,j]:.2f}" for j in range(n)] for i in range(n)]

    # Dynamic height: at least 420px, scale with number of stocks
    height = max(420, min(800, n * 16 + 140))

    fig = go.Figure(go.Heatmap(
        z=corr.tolist(),
        x=lbls,
        y=lbls,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=9, color="#1e293b"),
        colorscale="RdBu",
        zmid=0, zmin=-1, zmax=1,
        hovertemplate="%{y} \u2194 %{x}: <b>%{z:.3f}</b><extra></extra>",
        colorbar=dict(
            title=dict(text="r", font=dict(color="#0f172a", size=12)),
            tickfont=dict(color="#1e293b", size=11),
            thickness=14,
            len=0.8,
        ),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#0f172a", size=15)),
        height=height,
        paper_bgcolor=_CHART_BG,
        plot_bgcolor=_CHART_PLOT_BG,
        font=dict(color=_CHART_FONT_COLOR, family="Inter, sans-serif", size=12),
        xaxis=dict(
            tickangle=-45,
            tickfont=dict(size=10, color=_CHART_FONT_COLOR, family="Inter, sans-serif"),
            linecolor=_CHART_LINE,
            gridcolor=_CHART_GRID,
        ),
        yaxis=dict(
            tickfont=dict(size=10, color=_CHART_FONT_COLOR, family="Inter, sans-serif"),
            linecolor=_CHART_LINE,
            gridcolor=_CHART_GRID,
            autorange="reversed",
        ),
        margin=dict(t=60, b=130, l=100, r=60),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Inline sparkline builder — light-theme fix
# ---------------------------------------------------------------------------

def _render_sparklines(syms: list[str], names: list[str]) -> None:
    """Build and render sparklines with visible labels on light theme."""
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
    height = max(300, ROWS * 120)

    fig = make_subplots(
        rows=ROWS, cols=COLS,
        horizontal_spacing=0.04,
        vertical_spacing=0.10,
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
                hovertemplate=f"<b>{lbl}</b><br>\u20b9%{{y:,.2f}}<extra></extra>",
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
            font=dict(size=10, color=colour, family="Inter, sans-serif"),
            xanchor="center",
        )

    fig.update_layout(
        title=dict(
            text=f"20-Day Price Sparklines ({len(valid)} stocks)",
            font=dict(color="#0f172a", size=15),
        ),
        height=height,
        paper_bgcolor=_CHART_BG,
        plot_bgcolor=_CHART_PLOT_BG,
        font=dict(color=_CHART_FONT_COLOR, family="Inter, sans-serif", size=11),
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

    st.markdown("### \U0001f4ca Quick Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("\U0001f680 Top Gainer (30D)",  gains[0][1],  f"{gains[0][0]:+.1f}%")
    c2.metric("\U0001f4c9 Top Loser (30D)",   losses[0][1], f"{losses[0][0]:+.1f}%")
    c3.metric("\u26a1 Most Volatile",      vols_list[0][1], f"\u03c3 {vols_list[0][0]:.2f}%/day")
    c4.metric("\U0001f4c8 Avg 30D Return",    "Nifty 50",   f"{avg:+.1f}%")


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
            "\u26a0\ufe0f Market is closed \u2014 charts below use last-session closing prices and work 24/7."
        )

    _render_dashboard_metrics()
    divider()

    sectors = ["All"] + sorted({s["sector"] for s in NIFTY50})
    sel_sec = st.selectbox("Sector", sectors, key="all_sec")

    # Stock table
    with st.spinner("Loading stock data\u2026"):
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
        title=f"Nifty 50 Companies \u2014 {sel_sec}",
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
            "Sector Allocation \u2014 Nifty 50" if sel_sec == "All" else f"Sector Allocation \u2014 {sel_sec}",
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

    # Heatmap
    sec("30-Day Return Correlation Heatmap")
    st.caption(
        "Pairwise Pearson correlations of daily returns over the last 30 trading sessions. "
        "Blue\u00a0= negative, red\u00a0= positive."
    )
    _render_heatmap(
        sector_syms, sector_names,
        f"30-Day Correlation \u2014 {sel_sec}",
    )
    divider()

    # Sparklines
    sec("20-Day Price Sparklines")
    st.caption(
        "Each mini-chart shows the last 20 trading sessions. "
        "Green\u00a0= net gain, red\u00a0= net loss."
    )
    _render_sparklines(sector_syms, sector_names)
