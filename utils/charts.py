"""Plotly chart builders — pure functions that return go.Figure objects.

No Streamlit calls here.  app.py calls st.plotly_chart(build_*(...)).
"""
import plotly.graph_objects as go
import plotly.express as px

from utils.constants import PLT_TEMPLATE, PLT_LAYOUT, AXIS_STYLE


def _style(fig):
    """Apply the shared axis style to a Figure and return it."""
    try:
        fig.update_xaxes(**AXIS_STYLE)
        fig.update_yaxes(**AXIS_STYLE)
    except Exception:
        pass
    return fig


# ---------------------------------------------------------------------------
# Price charts (Line / Candlestick / Area)
# ---------------------------------------------------------------------------

def build_price_chart(df, name, period, chart_type="Line",
                      y_title="Price (Rs.)", height=440):
    """Universal OHLCV price chart.

    Parameters
    ----------
    df         : DataFrame with Open/High/Low/Close columns
    name       : display name for the series
    period     : period string shown in the title (e.g. '3mo')
    chart_type : 'Line' | 'Candlestick' | 'Area'
    y_title    : y-axis label
    height     : chart height in px
    """
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
    else:  # Line
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"], name=name,
            line=dict(color="#6366f1", width=2.5),
        ))
    fig.update_layout(
        **PLT_LAYOUT,
        title=f"{name} - {period}",
        height=height,
        xaxis_title="Date",
        yaxis_title=y_title,
    )
    return _style(fig)


# ---------------------------------------------------------------------------
# Bar charts
# ---------------------------------------------------------------------------

def build_pct_bar(df, x_col, y_col, title, text_col=None, height=360):
    """Coloured diverging bar chart for % change columns."""
    fig = px.bar(
        df, x=x_col, y=y_col,
        color=y_col,
        color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
        color_continuous_midpoint=0,
        text=text_col or y_col,
        title=title,
        template=PLT_TEMPLATE,
        height=height,
    )
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
    return _style(fig)


def build_closing_bar(df, x_col, y_col, title, height=360):
    """Simple continuous-colour bar chart for absolute price columns."""
    fig = px.bar(
        df, x=x_col, y=y_col, color=y_col,
        color_continuous_scale=["#6366f1", "#06b6d4", "#10b981"],
        title=title,
        template=PLT_TEMPLATE,
        height=height,
    )
    fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
    return _style(fig)


# ---------------------------------------------------------------------------
# Normalised multi-line trend chart
# ---------------------------------------------------------------------------

def build_trend_chart(series_dict, title="Normalised Performance (base=100)",
                      height=360):
    """Plot multiple normalised price series on one figure.

    Parameters
    ----------
    series_dict : {name: {"df": DataFrame, "color": hex_str}}
    """
    fig = go.Figure()
    for name, meta in series_dict.items():
        df    = meta["df"]
        color = meta.get("color", "#6366f1")
        if df.empty or "Close" not in df.columns:
            continue
        norm = df["Close"] / df["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=df.index, y=norm, name=name,
            mode="lines", line=dict(color=color, width=2),
        ))
    fig.add_hline(y=100, line_dash="dot", line_color="#94a3b8")
    fig.update_layout(
        **PLT_LAYOUT,
        title=title,
        height=height,
        xaxis_title="Date",
        yaxis_title="Indexed Value",
    )
    return _style(fig)
