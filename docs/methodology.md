# Methodology

This page explains how the tracker fetches data, calculates metrics, and how the optional ML prediction pipeline is designed. Transparency here builds trust with users and contributors.

---

## Data Source

All market data is sourced from **Yahoo Finance** via the [`yfinance`](https://github.com/ranaroussi/yfinance) Python library, which wraps Yahoo's unofficial API.

```
User request
    └── Streamlit UI
            └── utils/data.py  ──── yfinance.Ticker.history(period, interval)
                                         └── Yahoo Finance API
```

!!! info "Market Data Disclaimer"
    Yahoo Finance data may be delayed by up to 15 minutes. This app is for educational and informational purposes only — not financial advice.

---

## Market State Detection

The `is_nse_open()` function in `utils/data.py` determines whether the NSE is currently live:

1. Converts current time to **IST (Asia/Kolkata)**
2. Checks if today is a **weekday** (Monday–Friday)
3. Checks if current time is between **09:15 AM – 03:30 PM IST**
4. Returns a tuple: `(is_open: bool, status_message: str, last_close_label: str)`

!!! note "NSE Holidays"
    NSE market holidays are not currently hardcoded. The market-state check uses weekdays + trading hours only. Contributions to add a holiday calendar are welcome — see [Contributing](contributing.md).

---

## Price Change Calculation

For all stocks and indices, the **1-day percentage change** is calculated as:

```
% Change = ((Current Close - Previous Close) / Previous Close) × 100
```

This is implemented in `utils/calculations.py` → `build_stock_rows()`.

---

## P&L Calculator

The `calc_pl()` function computes three values given buy price, sell price, and quantity:

```
Investment  = buy_price × quantity
P&L         = (sell_price − buy_price) × quantity
Return (%)  = (P&L / Investment) × 100
```

### Beta-Adjusted Impact

The beta-adjusted simulation (`calc_beta_impact()`) estimates how a given Nifty move affects a stock:

```
Stock Move (%) = Nifty Move (%) × Beta
New Price      = Buy Price × (1 + Stock Move / 100)
P&L Impact     = (New Price − Buy Price) × Quantity
```

**Beta** measures a stock's sensitivity to Nifty movements. A beta of 1.5 means the stock is expected to move 1.5× the index.

---

## Caching Strategy

To avoid hitting Yahoo Finance on every Streamlit re-render, `@st.cache_data(ttl=CACHE_TTL)` is applied to all data-fetching functions. The default TTL is **60 seconds** when the market is open, keeping data reasonably fresh without excessive API calls.

---

## Time Machine

The **Time Machine** tab pre-fetches the full 5-year history for all 50 stocks in a single cached call (`fetch_all_history()`). It then filters to the closest available trading day to the user-selected date using `build_time_machine_snapshot()`. The first load may take 30–60 seconds; subsequent loads within the same session are instant.

---

## Future: ML Price Prediction (Roadmap)

A planned extension is an LSTM-based 5-day price forecast per stock. The intended architecture:

| Component | Detail |
|---|---|
| **Model** | LSTM (Long Short-Term Memory) via TensorFlow/Keras |
| **Features** | Close price, MA20, MA50, RSI, MACD, Volume |
| **Window** | 60-day lookback to predict next 5 closing prices |
| **Training data** | 5 years of daily OHLCV per Nifty 50 stock |
| **Evaluation** | RMSE, MAE on hold-out 20% test split |
| **Uncertainty** | Monte Carlo Dropout for prediction intervals |

!!! warning
    ML price predictions are illustrative models, not investment advice. Past patterns do not guarantee future returns.
