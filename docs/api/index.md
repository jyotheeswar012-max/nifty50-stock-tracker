---
title: API Reference Overview
---

# API Reference

The Nifty 50 Tracker is structured as a set of **pure Python modules** that any contributor or integrator can import independently of Streamlit.

## Module Map

| Module | Import Path | Purpose |
|---|---|---|
| Data | `from utils.data import fetch_ticker` | All network I/O — fetches, caching, fallback logic |
| Calculations | `from utils.calculations import calc_pl` | Pure arithmetic — no I/O, 100% unit-testable |
| Charts | `from utils.charts import build_price_chart` | Plotly `Figure` builders — return objects, never render |
| Logger | `from utils.logger import get_logger` | Centralised logging setup |
| Constants | `from utils.constants import NIFTY50` | Symbols, colours, cache TTL, famous dates |

## Design Principles

!!! tip "Pure functions in `calculations.py` and `charts.py`"
    Neither module imports `streamlit`, `yfinance`, or any I/O library. Given the same inputs, they always return the same outputs. This makes them trivially testable with `pytest` and reusable outside a Streamlit context.

!!! info "All `fetch_*` functions are cached"
    Every public function in `utils/data.py` is decorated with `@st.cache_data`. Calling `fetch_ticker("RELIANCE.NS", "3mo")` twice within the TTL window returns the cached result without a network call.

## Quick Example

```python
from utils.data import fetch_ticker
from utils.calculations import calc_pl

# Fetch 3-month daily bars for Reliance Industries
df = fetch_ticker("RELIANCE.NS", "3mo")

last_price = df["Close"].iloc[-1]   # e.g. 1307.50

# Calculate P&L for a position
pl, investment, return_pct = calc_pl(
    buy_price=1250.0,
    sell_price=last_price,
    qty=100,
)
print(f"P&L: ₹{pl:,.2f}  |  Return: {return_pct:.2f}%")
# P&L: ₹5,750.00  |  Return: 4.60%
```
