# Calculation Functions — `utils/calculations.py`

All business logic — P&L math, stock row building, beta impact — lives here, independent of the UI.

---

## `safe_float(value, default)`

```python
def safe_float(value, default: float = 0.0) -> float:
```

Safely coerces any value to `float`, returning `default` on failure. Prevents crashes when Yahoo Finance returns `NaN` or `None`.

---

## `calc_pl(buy_price, sell_price, qty)`

```python
def calc_pl(
    buy_price: float,
    sell_price: float,
    qty: int
) -> tuple[float, float, float]:
```

Calculates P&L for a trade.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `buy_price` | `float` | Price at which shares were bought (Rs.) |
| `sell_price` | `float` | Price at which shares were sold / current market price (Rs.) |
| `qty` | `int` | Number of shares |

**Returns:** `(pnl, investment, return_pct)`

| Return | Formula |
|---|---|
| `pnl` | `(sell_price − buy_price) × qty` |
| `investment` | `buy_price × qty` |
| `return_pct` | `(pnl / investment) × 100` |

**Example:**
```python
from utils.calculations import calc_pl

pnl, invested, ret = calc_pl(buy_price=2500, sell_price=2800, qty=10)
print(f"P&L: ₹{pnl:,.2f} | Return: {ret:.2f}%")
# P&L: ₹3,000.00 | Return: 12.00%
```

---

## `calc_beta_impact(nifty_move_pct, buy_price, qty, beta)`

```python
def calc_beta_impact(
    nifty_move_pct: float,
    buy_price: float,
    qty: int,
    beta: float
) -> tuple[float, float, float, float, float, float]:
```

Simulates a stock's price change given a Nifty index move and a beta coefficient.

**Formula:**
```
stock_move_pct  = nifty_move_pct × beta
price_change    = buy_price × (stock_move_pct / 100)
new_price       = buy_price + price_change
pnl_impact      = price_change × qty
```

**Returns:** `(stock_move_pct, price_change, new_price, old_value, new_value, pnl_impact)`

---

## `build_stock_rows(data_5d, market_open, fetch_intraday_fn)`

```python
def build_stock_rows(
    data_5d: dict,
    market_open: bool,
    fetch_intraday_fn: Callable
) -> pd.DataFrame:
```

Builds the master table of all 50 Nifty stocks with current price, 1-day change, and sector. When the market is open, calls `fetch_intraday_fn` to get a live price; when closed, uses the last available closing price.

**Returns:** `pd.DataFrame` with columns:
`Symbol, Company, Sector, Price / Last Close, Change (pts), Change (%), _curr, _pct`

---

## `build_time_machine_snapshot(all_history, target_date)`

```python
def build_time_machine_snapshot(
    all_history: dict,
    target_date: date
) -> pd.DataFrame:
```

Filters the pre-fetched 5-year history to return a snapshot of all 50 stocks as close as possible to `target_date`. If the exact date has no trading data (e.g. a weekend), it falls back to the nearest previous trading day.
