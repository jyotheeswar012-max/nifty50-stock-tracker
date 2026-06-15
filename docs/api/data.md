# Data Functions — `utils/data.py`

All data-fetching logic is isolated in `utils/data.py`. Functions are designed to be pure (no Streamlit side-effects) so they can be tested and reused outside the UI.

---

## `is_nse_open()`

```python
def is_nse_open() -> tuple[bool, str, str]:
```

Determines whether the NSE market is currently trading.

**Returns:** `(is_open, status_message, last_close_label)`

| Return | Type | Description |
|---|---|---|
| `is_open` | `bool` | `True` if currently within NSE trading hours (Mon–Fri, 09:15–15:30 IST) |
| `status_message` | `str` | Human-readable status, e.g. `"Market opens at 09:15 AM"` |
| `last_close_label` | `str` | Label for the last session, e.g. `"Last close: Fri 13 Jun"` |

**Example:**
```python
from utils.data import is_nse_open

open_, status, label = is_nse_open()
if open_:
    print("NSE is live")
else:
    print(f"NSE closed — {status}")
```

---

## `fetch_ticker(symbol, period)`

```python
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame:
```

Fetches OHLCV history for a single ticker.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `symbol` | `str` | — | Yahoo Finance ticker symbol, e.g. `"^NSEI"`, `"RELIANCE.NS"` |
| `period` | `str` | `"3mo"` | yfinance period string: `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y` |

**Returns:** `pd.DataFrame` with columns `Open, High, Low, Close, Volume` and a `DatetimeIndex`.

**Example:**
```python
from utils.data import fetch_ticker

nifty = fetch_ticker("^NSEI", "1y")
print(nifty.tail())
```

---

## `fetch_intraday(symbol)`

```python
def fetch_intraday(symbol: str) -> pd.DataFrame:
```

Fetches today's 5-minute intraday candles for a stock. Used to compute live price when the market is open.

**Returns:** `pd.DataFrame` with 5-minute OHLCV data, or an empty DataFrame on failure.

---

## `fetch_indices()`

```python
def fetch_indices() -> dict[str, pd.DataFrame]:
```

Fetches recent OHLCV history for all NSE indices defined in `utils/constants.py → NSE_INDICES`.

**Returns:** `dict` mapping each index symbol to its OHLCV DataFrame.

---

## `fetch_all_stocks_5d()`

```python
def fetch_all_stocks_5d() -> dict[str, pd.DataFrame]:
```

Batch-fetches the last 5 trading days of data for all 50 Nifty stocks. Used to populate the **All 50 Companies** and **Gainers & Losers** tabs.

!!! tip
    This function is wrapped in `@st.cache_data(ttl=CACHE_TTL)` in `app.py` to prevent redundant API calls.

---

## `fetch_all_history()`

```python
def fetch_all_history() -> dict[str, pd.DataFrame]:
```

Fetches 5 years of daily history for all 50 Nifty stocks. Used exclusively by the **Time Machine** tab.

!!! warning "Performance"
    This call can take 30–60 seconds on the first load. Results are cached for the Streamlit session lifetime (`ttl=3600`).
