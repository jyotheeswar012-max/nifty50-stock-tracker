"""Plotly chart builders — pure functions that return go.Figure objects.

No Streamlit calls here.  Page modules call st.plotly_chart(build_*(...)).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.constants import AXIS_STYLE, PLT_LAYOUT, PLT_TEMPLATE
from utils.logger import get_logger

log = get_logger(__name__)


def _style(fig: go.Figure) -> go.Figure:
    try:
        fig.update_xaxes(**AXIS_STYLE)
        fig.update_yaxes(**AXIS_STYLE)
    except Exception as exc:
        log.warning("_style(): failed: %s", exc)
    return fig


# ---------------------------------------------------------------------------
# Price charts (Line / Candlestick / Area)
# ---------------------------------------------------------------------------

def build_price_chart(df, name, period, chart_type="Line",
                      y_title="Price (Rs.)", height=440):
    """Universal OHLCV price chart."""
    log.debug("build_price_chart: name=%s period=%s type=%s rows=%d",
              name, period, chart_type, len(df))
    try:
        fig = go.Figure()
        if chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name=name,
                increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            ))
        elif chart_type == "Area":
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Close"], fill="tozeroy", name=name,
                line=dict(color="#6366f1", width=2),
                fillcolor="rgba(99,102,241,0.12)",
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Close"], name=name,
                line=dict(color="#6366f1", width=2.5),
            ))
        fig.update_layout(
            **PLT_LAYOUT, title=f"{name} - {period}", height=height,
            xaxis_title="Date", yaxis_title=y_title,
        )
        return _style(fig)
    except Exception as exc:
        log.error("build_price_chart failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Bar charts
# ---------------------------------------------------------------------------

def build_pct_bar(df, x_col, y_col, title, text_col=None, height=360):
    """Coloured diverging bar chart for % change columns."""
    log.debug("build_pct_bar: title=%s rows=%d", title, len(df))
    try:
        fig = px.bar(
            df, x=x_col, y=y_col,
            color=y_col,
            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
            color_continuous_midpoint=0,
            text=text_col or y_col,
            title=title, template=PLT_TEMPLATE, height=height,
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
        return _style(fig)
    except Exception as exc:
        log.error("build_pct_bar failed: %s", exc, exc_info=True)
        return go.Figure()


def build_closing_bar(df, x_col, y_col, title, height=360):
    """Simple continuous-colour bar for absolute price columns."""
    log.debug("build_closing_bar: title=%s rows=%d", title, len(df))
    try:
        fig = px.bar(
            df, x=x_col, y=y_col, color=y_col,
            color_continuous_scale=["#6366f1", "#06b6d4", "#10b981"],
            title=title, template=PLT_TEMPLATE, height=height,
        )
        fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
        return _style(fig)
    except Exception as exc:
        log.error("build_closing_bar failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Normalised multi-line trend chart
# ---------------------------------------------------------------------------

def build_trend_chart(series_dict, title="Normalised Performance (base=100)",
                      height=360):
    """Plot multiple normalised price series on one figure."""
    log.debug("build_trend_chart: series=%s", list(series_dict.keys()))
    try:
        fig = go.Figure()
        for name, meta in series_dict.items():
            df    = meta["df"]
            color = meta.get("color", "#6366f1")
            if df.empty or "Close" not in df.columns:
                log.warning("build_trend_chart: skipping %s (empty)", name)
                continue
            norm = df["Close"] / df["Close"].iloc[0] * 100
            fig.add_trace(go.Scatter(
                x=df.index, y=norm, name=name,
                mode="lines", line=dict(color=color, width=2),
            ))
        fig.add_hline(y=100, line_dash="dot", line_color="#94a3b8")
        fig.update_layout(
            **PLT_LAYOUT, title=title, height=height,
            xaxis_title="Date", yaxis_title="Indexed Value",
        )
        return _style(fig)
    except Exception as exc:
        log.error("build_trend_chart failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Sector allocation pie
# ---------------------------------------------------------------------------

def build_sector_pie(df_rows: pd.DataFrame, title: str = "Sector Allocation",
                     height: int = 420) -> go.Figure:
    """Donut chart — weighted by current price sum per sector."""
    log.debug("build_sector_pie: rows=%d cols=%s", len(df_rows), list(df_rows.columns))
    try:
        if "Sector" not in df_rows.columns:
            raise ValueError("'Sector' column missing from df_rows")

        if "_curr" in df_rows.columns:
            # Explicit numeric cast on a plain copy — avoids pandas MultiIndex
            # column bug that occurs with groupby().apply() in newer pandas.
            tmp = df_rows[["Sector", "_curr"]].copy()
            tmp["_curr"] = pd.to_numeric(tmp["_curr"], errors="coerce")
            tmp = tmp.dropna(subset=["_curr"])
            grp = tmp.groupby("Sector", as_index=False)["_curr"].sum()
            grp = grp.rename(columns={"_curr": "Value"})
            values_col, value_label = "Value", "Cumulative Price (Rs.)"
        else:
            grp = df_rows.groupby("Sector", as_index=False).size()
            grp = grp.rename(columns={"size": "Count"})
            values_col, value_label = "Count", "Stock Count"

        grp = grp[grp[values_col] > 0].copy()

        if grp.empty:
            log.warning("build_sector_pie: no sectors with positive value after filter")
            return go.Figure()

        _PALETTE = [
            "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#06b6d4",
            "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#84cc16",
            "#0ea5e9", "#a78bfa",
        ]

        fig = go.Figure(go.Pie(
            labels=grp["Sector"],
            values=grp[values_col],
            hole=0.45,
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>" + value_label + ": %{value:,.0f}<br>Share: %{percent}<extra></extra>",
            marker=dict(colors=_PALETTE[:len(grp)], line=dict(color="#ffffff", width=2)),
        ))
        fig.update_layout(
            **PLT_LAYOUT,
            title=title,
            height=height,
            legend=dict(orientation="v", x=1.02, y=0.5),
            margin=dict(t=60, b=20, l=20, r=160),
        )
        return fig
    except Exception as exc:
        log.error("build_sector_pie failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Correlation heatmap
# ---------------------------------------------------------------------------

def build_correlation_heatmap(
    all_hist: dict,
    symbols: list[str],
    labels: list[str] | None = None,
    title: str = "30-Day Return Correlation",
    height: int = 580,
) -> go.Figure:
    """Heatmap of pairwise Pearson correlations of daily returns."""
    log.debug("build_correlation_heatmap: %d symbols", len(symbols))
    try:
        if labels is None:
            labels = [s.replace(".NS", "") for s in symbols]

        closes: dict[str, pd.Series] = {}
        for sym, lbl in zip(symbols, labels):
            h = all_hist.get(sym)
            if h is not None and not h.empty and "Close" in h.columns:
                closes[lbl] = h["Close"].sort_index()

        if len(closes) < 2:
            log.warning("build_correlation_heatmap: fewer than 2 valid series")
            return go.Figure()

        price_df = pd.DataFrame(closes).dropna(how="all")
        returns  = price_df.pct_change().dropna(how="all").tail(30)
        corr     = returns.corr()

        z    = corr.values
        text = [[f"{v:.2f}" for v in row] for row in z]

        fig = go.Figure(go.Heatmap(
            z=z,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=10),
            colorscale="RdBu",
            zmid=0,
            zmin=-1, zmax=1,
            hovertemplate="%{y} \u2194 %{x}: <b>%{z:.3f}</b><extra></extra>",
            colorbar=dict(title="r", thickness=12, len=0.8),
        ))
        fig.update_layout(
            **PLT_LAYOUT,
            title=title,
            height=height,
            xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
            yaxis=dict(tickfont=dict(size=10)),
            margin=dict(t=60, b=120, l=80, r=60),
        )
        return fig
    except Exception as exc:
        log.error("build_correlation_heatmap failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Sparkline mini-chart table
# ---------------------------------------------------------------------------

def build_sparkline_table(
    stock_hist: dict,
    symbols: list[str],
    labels: list[str] | None = None,
    lookback: int = 20,
    height: int = 560,
) -> go.Figure:
    """Small multiples: one sparkline per Nifty50 stock in a 5-column grid."""
    log.debug("build_sparkline_table: %d symbols lookback=%d", len(symbols), lookback)
    try:
        if labels is None:
            labels = [s.replace(".NS", "") for s in symbols]

        valid_pairs = [
            (sym, lbl)
            for sym, lbl in zip(symbols, labels)
            if stock_hist.get(sym) is not None
            and not stock_hist[sym].empty
            and "Close" in stock_hist[sym].columns
        ]

        if not valid_pairs:
            log.warning("build_sparkline_table: no valid series")
            return go.Figure()

        COLS = 5
        ROWS = (len(valid_pairs) + COLS - 1) // COLS

        fig = make_subplots(
            rows=ROWS, cols=COLS,
            horizontal_spacing=0.04,
            vertical_spacing=0.06,
        )

        for idx, (sym, lbl) in enumerate(valid_pairs):
            row = idx // COLS + 1
            col = idx % COLS + 1
            close = stock_hist[sym]["Close"].sort_index().tail(lookback)
            pct_chg = (close.iloc[-1] / close.iloc[0] - 1) * 100 if len(close) >= 2 else 0.0
            colour  = "#10b981" if pct_chg >= 0 else "#ef4444"

            fig.add_trace(
                go.Scatter(
                    x=list(range(len(close))),
                    y=close.values,
                    mode="lines",
                    line=dict(color=colour, width=1.5),
                    name=lbl,
                    hovertemplate=f"<b>{lbl}</b><br>Day %{{x}}<br>\u20b9%{{y:,.2f}}<extra></extra>",
                    showlegend=False,
                ),
                row=row, col=col,
            )
            fig.update_xaxes(showticklabels=False, row=row, col=col)
            fig.update_yaxes(showticklabels=False, row=row, col=col)

            fig.add_annotation(
                text=f"<b>{lbl}</b> {pct_chg:+.1f}%",
                xref="paper", yref="paper",
                x=(col - 0.5) / COLS,
                y=1.0 - (row - 1) / ROWS + 0.005,
                showarrow=False,
                font=dict(size=9, color=colour),
                xanchor="center",
            )

        fig.update_layout(
            **PLT_LAYOUT,
            title=f"20-Day Price Sparklines (last {lookback} sessions)",
            height=height,
            margin=dict(t=80, b=20, l=10, r=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig
    except Exception as exc:
        log.error("build_sparkline_table failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Static fallback history — always-available synthetic OHLCV data
# ---------------------------------------------------------------------------

def _build_static_history() -> dict[str, pd.DataFrame]:
    """Generate 35 business days of deterministic synthetic OHLCV for all 50
    Nifty stocks.  Seeded per-symbol via MD5 so values are stable across
    page refreshes.  Called when live yfinance data is unavailable so that
    Sector Pie, Correlation Heatmap and Sparklines always render.
    """
    _SEED: dict[str, float] = {
        "RELIANCE.NS": 1480,   "HDFCBANK.NS": 1920,  "ICICIBANK.NS": 1340,
        "INFY.NS": 1780,       "TCS.NS": 4050,        "BHARTIARTL.NS": 1850,
        "ITC.NS": 480,         "KOTAKBANK.NS": 1890,  "LT.NS": 3580,
        "HCLTECH.NS": 1920,    "AXISBANK.NS": 1245,   "SBIN.NS": 820,
        "BAJFINANCE.NS": 7200, "WIPRO.NS": 580,       "ASIANPAINT.NS": 2380,
        "MARUTI.NS": 12800,    "SUNPHARMA.NS": 1720,  "TITAN.NS": 3540,
        "ULTRACEMCO.NS": 11500, "ONGC.NS": 275,       "NTPC.NS": 365,
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
    _VOL: dict[str, float] = {
        "RELIANCE.NS": 0.012,  "HDFCBANK.NS": 0.013,  "ICICIBANK.NS": 0.015,
        "INFY.NS": 0.014,      "TCS.NS": 0.012,        "BHARTIARTL.NS": 0.013,
        "ITC.NS": 0.010,       "KOTAKBANK.NS": 0.013,  "LT.NS": 0.014,
        "HCLTECH.NS": 0.013,   "AXISBANK.NS": 0.016,   "SBIN.NS": 0.017,
        "BAJFINANCE.NS": 0.018, "WIPRO.NS": 0.013,     "ASIANPAINT.NS": 0.011,
        "MARUTI.NS": 0.014,    "SUNPHARMA.NS": 0.012,  "TITAN.NS": 0.014,
        "ULTRACEMCO.NS": 0.013, "ONGC.NS": 0.015,      "NTPC.NS": 0.013,
        "POWERGRID.NS": 0.012, "M&M.NS": 0.015,        "TATAMOTORS.NS": 0.019,
        "TATASTEEL.NS": 0.020, "JSWSTEEL.NS": 0.019,   "HINDALCO.NS": 0.018,
        "ADANIENT.NS": 0.022,  "ADANIPORTS.NS": 0.016, "BAJAJFINSV.NS": 0.016,
        "BAJAJAUTO.NS": 0.013, "HEROMOTOCO.NS": 0.013, "CIPLA.NS": 0.012,
        "DRREDDY.NS": 0.011,   "DIVISLAB.NS": 0.012,   "EICHERMOT.NS": 0.014,
        "GRASIM.NS": 0.013,    "HDFCLIFE.NS": 0.013,   "SBILIFE.NS": 0.013,
        "INDUSINDBK.NS": 0.019, "TATACONSUM.NS": 0.013, "BRITANNIA.NS": 0.011,
        "NESTLEIND.NS": 0.010, "HINDUNILVR.NS": 0.011, "COALINDIA.NS": 0.014,
        "BPCL.NS": 0.016,      "TECHM.NS": 0.014,      "LTF.NS": 0.018,
        "SHRIRAMFIN.NS": 0.016, "BEL.NS": 0.016,
    }

    result: dict[str, pd.DataFrame] = {}
    dates = pd.bdate_range(end="2026-06-17", periods=35)

    for sym, seed_price in _SEED.items():
        seed_int = int(hashlib.md5(sym.encode()).hexdigest()[:8], 16) % (2 ** 31)
        rng = np.random.default_rng(seed_int)
        vol = _VOL.get(sym, 0.015)
        n   = len(dates)

        rets   = rng.normal(0.0002, vol, n)
        closes = np.zeros(n)
        closes[-1] = seed_price
        for i in range(n - 2, -1, -1):
            closes[i] = closes[i + 1] / (1.0 + rets[i + 1])

        spread = closes * vol * 0.8
        opens  = closes + rng.uniform(-spread * 0.5, spread * 0.5)
        highs  = np.maximum(opens, closes) + np.abs(rng.normal(0, spread * 0.5))
        lows   = np.minimum(opens, closes) - np.abs(rng.normal(0, spread * 0.5))
        volume = rng.integers(500_000, 5_000_000, n).astype(float)

        result[sym] = pd.DataFrame(
            {"Open": opens, "High": highs, "Low": lows,
             "Close": closes, "Volume": volume},
            index=dates,
        )
    return result
