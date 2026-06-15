---
title: Calculation Functions
---

# `utils.calculations` — Pure Calculations

All functions here are **pure** — no network calls, no Streamlit imports, no side effects. Given the same inputs, they always return the same outputs. This makes the entire module testable with `pytest` without mocking.

---

## `safe_float(val, default=0.0)`

```python
def safe_float(val, default=0.0) -> float
```

Safely converts any value to `float`, returning `default` for `NaN`, `Inf`, or unconvertible values.

```python
safe_float("1234.56")   # 1234.56
safe_float(float("nan")) # 0.0
safe_float(None, -1.0)   # -1.0
```

---

## `get_last_price(symbol, stock_data_5d, market_open, fetch_intraday_fn)`

```python
def get_last_price(
    symbol: str,
    stock_data_5d: dict[str, pd.DataFrame],
    market_open: bool,
    fetch_intraday_fn: Callable,
) -> tuple[float | None, float | None]
```

Returns `(current_price, previous_close)` at the highest available precision.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `symbol` | `str` | Yahoo Finance ticker (e.g. `"HDFC.NS"`) |
| `stock_data_5d` | `dict` | Output of `fetch_all_stocks_5d()` |
| `market_open` | `bool` | Pass the result of `is_nse_open()[0]` |
| `fetch_intraday_fn` | `Callable` | Pass `fetch_intraday` — injected for testability |

**Returns** `(current_price, previous_close)`. Either value is `None` if data is unavailable.

**Behaviour**

- When `market_open=True`: calls `fetch_intraday_fn(symbol)` and returns the last 1-minute close as `current_price`, with the last daily bar close as `previous_close`
- When `market_open=False`: returns the last two daily closes as `(current, previous)`

---

## `build_stock_rows(stock_data_5d, market_open, fetch_intraday_fn)`

```python
def build_stock_rows(
    stock_data_5d: dict[str, pd.DataFrame],
    market_open: bool,
    fetch_intraday_fn: Callable,
) -> pd.DataFrame
```

Builds the master stock table used by the All Companies, Gainers, and Losers tabs.

**Returns** `pd.DataFrame` with columns:

| Column | Description |
|---|---|
| `Symbol` | Ticker without `.NS` suffix |
| `Company` | Full company name |
| `Sector` | NSE sector classification |
| `Beta` | 1-year trailing beta (static) |
| `Price (Rs.)` / `Last Close (Rs.)` | Current price (header changes with market state) |
| `Change (Rs.)` | Absolute price change vs. previous close |
| `Change (%)` | Percentage change |
| `_curr` | Raw float current price (for sorting; dropped before display) |
| `_pct` | Raw float % change (for chart colouring; dropped before display) |

---

## `calc_pl(buy_price, sell_price, qty)`

```python
def calc_pl(
    buy_price: float,
    sell_price: float,
    qty: int,
) -> tuple[float, float, float]
```

Calculates P&L for a stock position.

**Returns** `(pl, investment, return_pct)` where:
- `pl` = `(sell_price - buy_price) × qty`
- `investment` = `buy_price × qty`
- `return_pct` = `pl / investment × 100`

```python
pl, inv, ret = calc_pl(1250.0, 1307.50, 100)
# pl=5750.0, inv=125000.0, ret=4.6
```

---

## `calc_beta_impact(nifty_pct, stock_price, qty, beta)`

```python
def calc_beta_impact(
    nifty_pct: float,
    stock_price: float,
    qty: int,
    beta: float,
) -> tuple[float, float, float, float, float, float]
```

Calculates the estimated impact of a Nifty move on a stock position.

**Returns** `(stock_move_pct, price_change, new_price, old_value, new_value, pl)`

| Return Value | Formula |
|---|---|
| `stock_move_pct` | `nifty_pct × beta` |
| `price_change` | `stock_price × stock_move_pct / 100` |
| `new_price` | `stock_price + price_change` |
| `old_value` | `stock_price × qty` |
| `new_value` | `new_price × qty` |
| `pl` | `price_change × qty` |

---

## `build_time_machine_snapshot(all_hist, target)`

```python
def build_time_machine_snapshot(
    all_hist: dict[str, pd.DataFrame],
    target: date | str,
) -> pd.DataFrame
```

Builds a cross-sectional snapshot of all 50 Nifty stocks on a specific historical date.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `all_hist` | `dict` | Output of `fetch_all_history()` |
| `target` | `date` or `str` | Target date — resolved to nearest trading day ±4 calendar days |

**Returns** `pd.DataFrame` indexed by `Symbol` with columns `Name`, `Sector`, `Open`, `High`, `Low`, `Close`, `Volume`. Returns empty DataFrame if no data found.
