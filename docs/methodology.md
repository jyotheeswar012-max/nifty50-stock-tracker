---
title: Methodology
description: How the Nifty 50 Tracker fetches, validates, and presents market data — without ML black boxes
---

# Methodology

This page explains *how* the tracker works under the hood — data sourcing, price precision, fallback logic, and what the app deliberately does not do.

---

## Design Philosophy

!!! quote "Transparency over prediction"
    This app is a **transparency tool**, not a trading signal generator. Every number shown on screen is sourced directly from exchange data with no transformation that could obscure its meaning. No ML models. No "predicted" prices. No buy/sell signals.

The Nifty 50 Tracker exists to answer one question clearly: *What is the NSE doing right now, and how does it compare to the past?*

---

## Data Sourcing

### Primary Source — Yahoo Finance (`yfinance`)

All price data starts with Yahoo Finance via the `yfinance` Python library. It provides:

- **Daily OHLCV bars** — Open, High, Low, Close, Volume for any historical period
- **1-minute intraday bars** — used during market hours for tick-precise current prices
- **Automatic split/dividend adjustment** — `auto_adjust=True` ensures all historical prices are comparable

NSE symbols use the `.NS` suffix (e.g., `RELIANCE.NS`). Index symbols use the `^` prefix (e.g., `^NSEI` for Nifty 50).

### Fallback Source — NSE India (`nselib`)

If yfinance returns empty data — due to API rate limits, network issues, or Yahoo Finance downtime — the app automatically retries via `nselib`, which hits the official NSE India REST API directly.

nselib data requires normalisation before use:
- Comma-stripped numeric columns (`"1,234.56"` → `1234.56`)
- `DD-MM-YYYY` date strings parsed with `dayfirst=True`
- Column names mapped from NSE's verbose labels to standard `Open/High/Low/Close/Volume`

### Stale Cache Guard

If both live sources fail, the last successful result for that symbol/period is served from an in-memory dictionary (`_STALE_STORE`). A visible `⚠️` warning is surfaced in the UI via `st.session_state["data_warnings"]`. The app never silently serves stale data.

```
Fetch Request
     │
     ▼
┌─────────────────┐    empty    ┌─────────────────┐    empty    ┌──────────────┐
│  Yahoo Finance  │ ──────────► │    nselib API   │ ──────────► │ Stale Cache  │
│   (yfinance)    │             │   (nselib)      │             │ + ⚠️ warning │
└─────────────────┘             └─────────────────┘             └──────────────┘
        │                               │                               │
        └───────────────────────────────┴───────────────────────────────┘
                                        │
                              pandas DataFrame returned
```

---

## Price Precision — Live vs. Closed

This is the most nuanced part of the data pipeline. Yahoo Finance's **daily bar** uses the official NSE adjusted close, which can differ by ₹0.50–₹1.50 from the exact last-traded tick.

To eliminate this discrepancy, the app uses a **two-mode price strategy**:

| Market State | Price Source | Precision |
|---|---|---|
| **Open** (9:15 AM–3:30 PM IST) | `yfinance` 1-minute bar → last tick | Matches NSE live feed |
| **Closed / Weekend** | `yfinance` 5-day daily bar → official close | Exact NSE official closing price |

The market state is determined by `is_nse_open()` in `utils/data.py`, which checks:
1. Day of week (Saturday/Sunday → closed)
2. Current IST time vs. 09:15–15:30 window

---

## Beta-Adjusted Impact Model

The P&L Calculator includes a **beta impact scenario** that answers: *"If Nifty moves X%, what happens to my stock position?"*

### How Beta Works

Beta (β) measures a stock's sensitivity to Nifty 50 movements:

- β = 1.0 → stock moves in line with Nifty
- β = 1.5 → stock moves 1.5× Nifty
- β = 0.6 → stock moves 0.6× Nifty (defensive)

### Calculation

Given a user-selected Nifty move percentage *n* and stock beta *β*:

```
stock_move_pct  = n × β
price_change    = current_price × (stock_move_pct / 100)
new_price       = current_price + price_change
p&l_impact      = price_change × quantity
```

This is a **linear approximation** valid for small moves (< ±10%). For larger moves, beta itself changes non-linearly — a known limitation acknowledged in the UI.

### Beta Values

Beta values are **static constants** stored in `utils/constants.py` alongside each stock's metadata. They were sourced from NSE's published data and reflect 1-year trailing beta. They are not recalculated at runtime.

!!! warning "Static beta limitation"
    Beta changes over time. The values in `constants.py` reflect a point-in-time estimate. For a live trading application, beta should be recalculated from rolling 252-day returns. This is a planned enhancement — see [Changelog](changelog.md).

---

## Time Machine — Historical Snapshots

The Time Machine tab lets users travel to any NSE trading day since 2010.

### Data Loading

`fetch_all_history()` fetches 5-year daily OHLCV for all 50 stocks + macro symbols (`USDINR=X`, `CL=F` crude oil, `GC=F` gold, `^NSEI`). This is a heavy fetch — ~50 API calls — so it is cached with a 1-hour TTL.

### Date Resolution

NSE does not trade every calendar day (weekends, holidays). The `nearest_row()` function searches ±4 calendar days around the requested date to find the nearest actual trading day:

```python
def nearest_row(df, target, window=4):
    for delta in range(window + 1):
        for sign in ([0] if delta == 0 else [1, -1]):
            candidate = target + pd.Timedelta(days=delta * sign)
            mask = df.index.normalize() == candidate.normalize()
            if mask.any():
                return df[mask].iloc[0]
    return None
```

If no trading day is found within ±4 days, the user sees an error message advising them to try a nearby date.

---

## What This App Deliberately Does Not Do

| Feature | Why It's Excluded |
|---|---|
| ML price prediction | Would create false confidence. Markets are not reliably predictable by simple models. |
| Buy / Sell signals | Regulatory and ethical risk. Not a licensed investment advisory service. |
| Real-time WebSocket feed | `yfinance` polls HTTP; a WebSocket feed would require an NSE-licensed broker API. |
| Portfolio tracking | Out of scope for v1; planned for v2 with optional Supabase backend. |
| Options / derivatives | NSE F&O data requires separate licensing. |
