---
title: Data Functions
---

# `utils.data` — Data Fetching

All network I/O lives here. Every public function is wrapped with `@st.cache_data` and implements the yfinance → nselib → stale-cache fallback chain.

---

## `is_nse_open()`

```python
def is_nse_open() -> tuple[bool, str, str]
```

Determines the current NSE market state based on IST time.

**Returns**

| Position | Type | Description |
|---|---|---|
| `[0]` | `bool` | `True` if market is currently open (9:15 AM–3:30 PM IST, weekdays only) |
| `[1]` | `str` | Status label: `"Open"`, `"Closed"`, `"Pre-Market"`, or `"Weekend"` |
| `[2]` | `str` | Human-readable last-close label (empty string when market is open) |

**Example**

```python
open_, status, last_close = is_nse_open()
# (False, 'Closed', 'Last Close: 15 Jun 2026, 3:30 PM IST')
```

---

## `fetch_ticker(symbol, period)`

```python
@st.cache_data(ttl=CACHE_TTL)
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame
```

Fetches daily OHLCV bars for a single symbol.

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `symbol` | `str` | — | Yahoo Finance ticker (e.g. `"RELIANCE.NS"`, `"^NSEI"`) |
| `period` | `str` | `"3mo"` | Lookback period: `"1d"`, `"5d"`, `"1mo"`, `"3mo"`, `"6mo"`, `"1y"`, `"2y"`, `"5y"` |

**Returns** `pd.DataFrame` with columns `Open`, `High`, `Low`, `Close`, `Volume` and a `DatetimeIndex`. Returns an empty DataFrame on failure — never raises.

**Example**

```python
df = fetch_ticker("TCS.NS", "1y")
print(df.tail(3))
#             Open     High      Low    Close  Volume
# 2026-06-13  3850.0  3891.5  3832.0  3877.20  987450
# 2026-06-14  3880.0  3905.0  3860.0  3890.00  1124300
# 2026-06-15  3895.0  3920.0  3875.5  3902.50  876200
```

---

## `fetch_intraday(symbol)`

```python
@st.cache_data(ttl=CACHE_TTL)
def fetch_intraday(symbol: str) -> pd.DataFrame
```

Fetches today's 1-minute OHLCV bars. Intended for use **during market hours only** — returns an empty DataFrame outside market hours.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `symbol` | `str` | Yahoo Finance ticker (e.g. `"INFY.NS"`) |

**Returns** `pd.DataFrame` with timezone-aware `DatetimeIndex` (Asia/Kolkata).

!!! note "Used internally by `get_last_price()`"
    You rarely need to call this directly. `build_stock_rows()` in `calculations.py` calls it via a passed-in function reference so it remains testable without network access.

---

## `fetch_indices()`

```python
@st.cache_data(ttl=CACHE_TTL)
def fetch_indices() -> dict[str, pd.DataFrame]
```

Fetches last-5-day daily bars for all indices defined in `utils.constants.NSE_INDICES`.

**Returns** `dict` mapping `symbol → DataFrame`. Missing symbols are omitted (not included as empty DataFrames).

---

## `fetch_all_stocks_5d()`

```python
@st.cache_data(ttl=CACHE_TTL)
def fetch_all_stocks_5d() -> dict[str, pd.DataFrame]
```

Fetches last-5-day daily bars for all 50 Nifty 50 stocks. Used by the All Companies, Gainers, and Losers tabs.

**Returns** `dict` mapping `symbol → DataFrame`. Symbols that fail all sources are omitted.

---

## `fetch_all_history()`

```python
@st.cache_data(ttl=3600)
def fetch_all_history() -> dict[str, pd.DataFrame]
```

Fetches 5-year daily OHLCV for all 50 Nifty stocks **plus** macro symbols: `USDINR=X`, `CL=F` (crude oil), `GC=F` (gold), `^NSEI`.

!!! warning "Heavy operation"
    This makes ~54 sequential API calls and can take 30–60 seconds on first load. It is cached for 1 hour (`ttl=3600`). Subsequent calls within the hour are instant.

---

## `get_source_status()`

```python
@st.cache_data(ttl=60)
def get_source_status() -> dict[str, str]
```

Probes each data source with a lightweight fetch and returns its current health.

**Returns** `dict` with keys `"yfinance"` and `"nselib"`, values one of: `"ok"`, `"degraded"`, `"down"`, `"not installed"`.

```python
status = get_source_status()
# {'yfinance': 'ok', 'nselib': 'not installed'}
```
