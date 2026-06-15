# Chart Functions — `utils/charts.py`

All Plotly figure builders. Each function returns a `plotly.graph_objects.Figure` which is rendered in the UI via `st.plotly_chart(fig, use_container_width=True)`.

---

## `build_price_chart(df, name, period, chart_type, ...)`

```python
def build_price_chart(
    df: pd.DataFrame,
    name: str,
    period: str,
    chart_type: str,        # "Line" | "Candlestick" | "Area"
    y_title: str = "Price (Rs.)",
    height: int = 400
) -> go.Figure:
```

Builds the main OHLCV price chart for a stock or index. Supports three chart types:

| `chart_type` | Visual | Best for |
|---|---|---|
| `"Line"` | Simple closing price line | Trend at a glance |
| `"Candlestick"` | OHLC candles with green/red coloring | Detailed price action |
| `"Area"` | Filled area under closing price | Cumulative trend emphasis |

---

## `build_pct_bar(df, x_col, y_col, title, ...)`

```python
def build_pct_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    text_col: str = None,
    height: int = 350
) -> go.Figure:
```

Builds a horizontal bar chart of percentage changes. Bars are colored **green** for positive and **red** for negative values automatically.

---

## `build_closing_bar(df, x_col, y_col, title)`

```python
def build_closing_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str
) -> go.Figure:
```

Builds a vertical bar chart of absolute closing prices. Used by the **Time Machine** tab to display a snapshot of all 50 stocks on a historical date.

---

## `build_trend_chart(series_dict, height)`

```python
def build_trend_chart(
    series_dict: dict,   # {"Index Name": {"df": DataFrame, "color": "#hex"}}
    height: int = 360
) -> go.Figure:
```

Builds a normalized multi-line trend comparison chart. All series are **rebased to 100** at the start of the period so indices with different absolute values can be compared on the same scale.

**Example input:**
```python
series = {
    "Nifty 50":  {"df": nifty_df,  "color": "#0d9488"},
    "Bank Nifty": {"df": bank_df,  "color": "#6366f1"},
}
fig = build_trend_chart(series)
```
