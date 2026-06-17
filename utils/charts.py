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
    log.debug("build_price_chart: name=%s period=%s type=%s rows=%d",
              name, period, chart_type, len(df))
    try:
        # Squeeze any MultiIndex DataFrame columns to Series
        def _s(col):
            v = df[col]
            return v.iloc[:, 0] if isinstance(v, pd.DataFrame) else v

        fig = go.Figure()
        if chart_type == "Candlestick":
            fig.add_trace(go.Candlestick(
                x=df.index, open=_s("Open"), high=_s("High"),
                low=_s("Low"), close=_s("Close"), name=name,
                increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            ))
        elif chart_type == "Area":
            fig.add_trace(go.Scatter(
                x=df.index, y=_s("Close"), fill="tozeroy", name=name,
                line=dict(color="#6366f1", width=2),
                fillcolor="rgba(99,102,241,0.12)",
            ))
        else:
            fig.add_trace(go.Scatter(
                x=df.index, y=_s("Close"), name=name,
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
    log.debug("build_trend_chart: series=%s", list(series_dict.keys()))
    try:
        fig = go.Figure()
        for name, meta in series_dict.items():
            df    = meta["df"]
            color = meta.get("color", "#6366f1")
            if df.empty or "Close" not in df.columns:
                log.warning("build_trend_chart: skipping %s (empty)", name)
                continue
            close_s = df["Close"].iloc[:, 0] if isinstance(df["Close"], pd.DataFrame) else df["Close"]
            norm = close_s / close_s.iloc[0] * 100
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
    log.debug("build_sector_pie: rows=%d cols=%s", len(df_rows), list(df_rows.columns))
    try:
        if "Sector" not in df_rows.columns:
            raise ValueError("'Sector' column missing from df_rows")

        if "_curr" in df_rows.columns:
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
            **PLT_LAYOUT, title=title, height=height,
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
    """Heatmap of pairwise Pearson correlations of daily returns.

    Robustness fixes
    ----------------
    1. Force all close series to float64 before building the DataFrame.
    2. Fill NaN in the correlation matrix with 0.0 so Plotly never gets NaN
       in the z-array (which causes an empty/invisible heatmap).
    3. Drop columns/rows that are still all-NaN after forward-fill.
    """
    log.debug("build_correlation_heatmap: %d symbols requested", len(symbols))
    try:
        if labels is None:
            labels = [s.replace(".NS", "") for s in symbols]

        closes: dict[str, pd.Series] = {}
        for sym, lbl in zip(symbols, labels):
            h = all_hist.get(sym)
            if h is None or h.empty:
                continue
            # Normalise column name
            col = None
            for candidate in ("Close", "Adj Close", "AdjClose"):
                if candidate in h.columns:
                    col = candidate
                    break
            if col is None:
                continue
            s = pd.to_numeric(h[col], errors="coerce").dropna()
            if len(s) < 5:
                continue
            closes[lbl] = s.sort_index().astype(float)

        log.debug("build_correlation_heatmap: %d valid series", len(closes))

        if len(closes) < 2:
            log.warning("build_correlation_heatmap: not enough valid series (%d)", len(closes))
            return go.Figure()

        price_df = pd.DataFrame(closes)
        # Forward-fill sparse gaps then drop rows still all-NaN
        price_df = price_df.ffill().dropna(how="all")

        returns = price_df.pct_change().replace([np.inf, -np.inf], np.nan)
        returns = returns.dropna(how="all").tail(30)

        if returns.shape[0] < 2:
            log.warning("build_correlation_heatmap: too few return rows after cleaning")
            return go.Figure()

        corr = returns.corr(min_periods=2)

        # KEY FIX: replace NaN with 0 so Plotly renders every cell
        z_raw = corr.values.astype(float)
        z = np.nan_to_num(z_raw, nan=0.0, posinf=1.0, neginf=-1.0)

        cols = corr.columns.tolist()
        rows = corr.index.tolist()
        text = [[f"{v:.2f}" for v in row] for row in z]

        fig = go.Figure(go.Heatmap(
            z=z,
            x=cols,
            y=rows,
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=9),
            colorscale="RdBu",
            zmin=-1, zmax=1,
            colorbar=dict(title="r", thickness=14),
        ))
        fig.update_layout(
            **PLT_LAYOUT, title=title, height=height,
            xaxis=dict(tickangle=-45, automargin=True),
            yaxis=dict(automargin=True),
            margin=dict(t=60, b=80, l=80, r=40),
        )
        return _style(fig)
    except Exception as exc:
        log.error("build_correlation_heatmap failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Sparkline (tiny inline chart)
# ---------------------------------------------------------------------------

def build_sparkline(prices: list[float], color: str = "#6366f1",
                    height: int = 60, width: int = 120) -> go.Figure:
    try:
        fig = go.Figure(go.Scatter(
            y=prices, mode="lines",
            line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=color.replace(")", ",0.15)").replace("rgb", "rgba") if "rgb" in color
                       else f"rgba(99,102,241,0.12)",
        ))
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=height, width=width,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        return fig
    except Exception as exc:
        log.error("build_sparkline failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Volume bar chart
# ---------------------------------------------------------------------------

def build_volume_chart(df: pd.DataFrame, name: str = "", height: int = 200) -> go.Figure:
    try:
        if "Volume" not in df.columns:
            return go.Figure()
        vol = df["Volume"].iloc[:, 0] if isinstance(df["Volume"], pd.DataFrame) else df["Volume"]
        close = df["Close"].iloc[:, 0] if isinstance(df["Close"], pd.DataFrame) else df["Close"]
        colors = [
            "#10b981" if i == 0 or close.iloc[i] >= close.iloc[i - 1] else "#ef4444"
            for i in range(len(close))
        ]
        fig = go.Figure(go.Bar(
            x=df.index, y=vol,
            marker_color=colors, name="Volume",
        ))
        fig.update_layout(
            **PLT_LAYOUT, title=f"{name} Volume", height=height,
            xaxis_title="Date", yaxis_title="Volume",
            margin=dict(t=40, b=40, l=40, r=20),
        )
        return _style(fig)
    except Exception as exc:
        log.error("build_volume_chart failed: %s", exc, exc_info=True)
        return go.Figure()


# ---------------------------------------------------------------------------
# Static histogram data builder (used when market is closed / yfinance down)
# ---------------------------------------------------------------------------

def _build_static_hist() -> dict[str, pd.DataFrame]:
    """Return a minimal static price history for all 50 Nifty symbols.

    Used as the last-resort fallback when every live source and the SQLite
    cache are unavailable (e.g. first cold-start with no internet).

    Prices are approximate end-of-2024 closing values and will never be
    used for trading decisions — only for layout/rendering purposes.
    """
    from utils.constants import NIFTY50
    import datetime

    base_date = datetime.date(2024, 12, 31)
    dates = pd.date_range(end=base_date, periods=30, freq="B")

    # Approximate last-known close prices (Dec 2024)
    static_prices: dict[str, float] = {
        "RELIANCE.NS": 1260, "TCS.NS": 4100, "HDFCBANK.NS": 1740,
        "INFY.NS": 1890, "ICICIBANK.NS": 1280, "BHARTIARTL.NS": 1580,
        "ITC.NS": 460,  "KOTAKBANK.NS": 1750, "LT.NS": 3500,
        "HCLTECH.NS": 1820, "AXISBANK.NS": 1130, "BAJFINANCE.NS": 6900,
        "WIPRO.NS": 310, "SUNPHARMA.NS": 1760, "TITAN.NS": 3300,
        "TATASTEEL.NS": 140, "MARUTI.NS": 10800, "NTPC.NS": 345,
        "ONGC.NS": 245, "POWERGRID.NS": 305, "ULTRACEMCO.NS": 11500,
        "NESTLEIND.NS": 2250, "ASIANPAINT.NS": 2300, "M&M.NS": 2900,
        "TECHM.NS": 1680, "BAJAJFINSV.NS": 1720, "TATAMOTORS.NS": 775,
        "ADANIENT.NS": 2400, "ADANIPORTS.NS": 1180, "SBIN.NS": 815,
        "COALINDIA.NS": 395, "HINDALCO.NS": 660, "JSWSTEEL.NS": 930,
        "BPCL.NS": 280, "CIPLA.NS": 1510, "DIVISLAB.NS": 5250,
        "DRREDDY.NS": 1270, "EICHERMOT.NS": 4700, "GRASIM.NS": 2540,
        "HDFCLIFE.NS": 680, "HEROMOTOCO.NS": 4300, "INDUSINDBK.NS": 960,
        "LTI.NS": 5200, "SBILIFE.NS": 1580, "SHREECEM.NS": 25000,
        "TATACONSUM.NS": 940, "TORNTPHARM.NS": 3100, "UPL.NS": 500,
        "VEDL.NS": 460, "ZOMATO.NS": 265,
    }

    result: dict[str, pd.DataFrame] = {}
    rng = np.random.default_rng(seed=42)
    for sym in [s["symbol"] for s in NIFTY50]:
        base = static_prices.get(sym, 1000)
        noise = rng.normal(0, base * 0.005, size=30)
        closes = np.maximum(base + np.cumsum(noise), 1.0)
        result[sym] = pd.DataFrame(
            {"Open": closes * 0.998, "High": closes * 1.005,
             "Low": closes * 0.995, "Close": closes, "Volume": 1_000_000},
            index=dates,
        )
    return result
