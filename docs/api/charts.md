---
title: Chart Functions
---

# `utils.charts` — Plotly Chart Builders

All functions return a `plotly.graph_objects.Figure` object. They never call `st.plotly_chart()` — that is the caller's responsibility. On failure, every function returns an **empty `go.Figure()`** and logs the error rather than raising.

---

## `build_price_chart(df, name, period, chart_type, y_title, height)`

```python
def build_price_chart(
    df: pd.DataFrame,
    name: str,
    period: str,
    chart_type: str = "Line",
    y_title: str = "Price (Rs.)",
    height: int = 440,
) -> go.Figure
```

Universal OHLCV price chart supporting three visual modes.

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `df` | `DataFrame` | — | OHLCV DataFrame from `fetch_ticker()` |
| `name` | `str` | — | Display name (chart title prefix) |
| `period` | `str` | — | Period label for title suffix |
| `chart_type` | `str` | `"Line"` | One of: `"Line"`, `"Candlestick"`, `"Area"` |
| `y_title` | `str` | `"Price (Rs.)"` | Y-axis label |
| `height` | `int` | `440` | Figure height in pixels |

**Chart Types**

| Type | Trace Used | Best For |
|---|---|---|
| `Line` | `go.Scatter` with no fill | Clean long-period trend view |
| `Candlestick` | `go.Candlestick` | Short periods — shows intraday OHLC range |
| `Area` | `go.Scatter` with `fill="tozeroy"` | Emphasis on absolute level |

---

## `build_pct_bar(df, x_col, y_col, title, text_col, height)`

```python
def build_pct_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    text_col: str | None = None,
    height: int = 360,
) -> go.Figure
```

Diverging colour bar chart for percentage change columns. Bars are green for positive values, red for negative, amber near zero.

---

## `build_closing_bar(df, x_col, y_col, title, height)`

```python
def build_closing_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    height: int = 360,
) -> go.Figure
```

Simple continuous-colour bar chart for absolute price values. Used by the Time Machine tab to show historical closing prices.

---

## `build_trend_chart(series_dict, title, height)`

```python
def build_trend_chart(
    series_dict: dict[str, dict],
    title: str = "Normalised Performance (base=100)",
    height: int = 360,
) -> go.Figure
```

Plots multiple price series **normalised to a common base of 100** for apples-to-apples comparison.

**`series_dict` format**

```python
series_dict = {
    "Nifty 50":  {"df": df_nsei,  "color": "#6366f1"},
    "Nifty Bank": {"df": df_bank, "color": "#10b981"},
    "Nifty IT":  {"df": df_it,   "color": "#f59e0b"},
}
```

Each entry must have `df` (a DataFrame with a `Close` column) and optionally `color` (hex string).
