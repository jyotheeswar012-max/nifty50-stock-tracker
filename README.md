# 📈 NSE & Nifty 50 — Ultimate Tracker + Time Machine

[![CI](https://github.com/jyotheeswar012-max/nifty50-stock-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/jyotheeswar012-max/nifty50-stock-tracker/actions/workflows/ci.yml)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nifty50-stock-tracker.streamlit.app)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend / UI** | [Streamlit](https://streamlit.io) — multi-page app with custom CSS |
| **Charts** | [Plotly](https://plotly.com/python/) — candlestick, heatmap, bar, scatter, line |
| **Market Data** | [yfinance](https://github.com/ranaroussi/yfinance) — NSE/BSE OHLCV via Yahoo Finance |
| **Data Layer** | [Pandas](https://pandas.pydata.org/) + [NumPy](https://numpy.org/) |
| **Caching** | `@st.cache_data` + SQLite (Parquet blobs) — 60s live / 5 min closed |
| **Auth** | [Supabase](https://supabase.com) + Firebase OTP (phone auth) |
| **ML / Predictions** | Beta-weighted CAPM model + scikit-learn signals |
| **Background Jobs** | `ThreadPoolExecutor` — parallel bulk data fetching |
| **Database** | [Supabase](https://supabase.com) (PostgreSQL) — watchlists, alerts, portfolios |
| **Logging** | Python `logging` with rotating file handler |
| **CI** | GitHub Actions — `ruff` lint + `pytest` |
| **Deployment** | [Streamlit Community Cloud](https://streamlit.io/cloud) |
| **Language** | Python 3.11+ |

---

> **Live App → [https://nifty50-stock-tracker.streamlit.app](https://nifty50-stock-tracker.streamlit.app)**

The **only free Nifty 50 dashboard** combining real-time NSE data with historical time-travel and macro event simulation.

---

## 🚀 10 Pages in One App

### 🟦 Live NSE Section
| Page | Features |
|------|----------|
| 🏦 NSE Market Overview | Live indices, advance/decline, multi-index trend |
| 📈 Nifty 50 Index | Candlestick + MA20/MA50 + volume + daily returns |
| 🏢 All 50 Companies | Live prices, sector filter, sort by price/change |
| 🏆 Gainers & Losers | Top N gainers/losers + treemap heatmap |
| 🧮 P&L Calculator | Actual vs assumed Nifty impact + sensitivity table |
| 🔍 Stock Chart Lookup | Any NSE stock — Candlestick/Line/Area + volume |

### ⏰ Time Machine Section
| Page | Features |
|------|----------|
| ⏰ Time Machine | Travel to any date — OHLC, gainers, heatmap, stock chart |
| 🧪 Scenario Engine | Rupee drop, oil spike, gold rally — estimated reactions per stock |
| 💼 Paper Portfolio | Invest on any date, track to any end date — full P&L + CAGR |
| 📅 Market Calendar | Monthly return heatmap + annual performance bar chart |

---

## 📡 Data API Documentation

This app uses the **[yfinance](https://github.com/ranaroussi/yfinance)** library as its data source. All market data is fetched via `yf.Ticker.history()` — no API key required.

### Core Fetch Functions

#### `fetch_ticker(symbol, period)`
Fetches OHLCV history for a single symbol.

| Parameter | Type | Example | Description |
|-----------|------|---------|-------------|
| `symbol` | `str` | `"^NSEI"`, `"RELIANCE.NS"` | Yahoo Finance ticker symbol |
| `period` | `str` | `"1mo"`, `"3mo"`, `"6mo"`, `"1y"`, `"2y"`, `"5y"` | Lookback window |

**Returns:** `pd.DataFrame` with columns `Open, High, Low, Close, Volume` and a `DatetimeIndex`.

```python
df = fetch_ticker("^NSEI", "3mo")
print(df.tail())  # Last 5 rows of Nifty 50
```

---

#### `fetch_indices()`
Fetches the last 5 trading days for all 8 NSE sector indices.

**Symbols covered:**

| Symbol | Index |
|--------|-------|
| `^NSEI` | Nifty 50 |
| `^NSEBANK` | Nifty Bank |
| `^CNXIT` | Nifty IT |
| `^CNXAUTO` | Nifty Auto |
| `^CNXPHARMA` | Nifty Pharma |
| `^CNXFMCG` | Nifty FMCG |
| `^CNXMETAL` | Nifty Metal |
| `^CNXREALTY` | Nifty Realty |

**Returns:** `dict[symbol → pd.DataFrame]`

---

#### `fetch_all_stocks_5d()`
Fetches the last 5 days of OHLCV data for all 50 Nifty stocks.

**Returns:** `dict[symbol → pd.DataFrame]`

---

#### `fetch_all_history()`
Fetches 5-year OHLCV history for all 50 Nifty stocks + macro proxies.

**Extra symbols:** `USDINR=X` (USD/INR), `CL=F` (Crude Oil), `GC=F` (Gold), `^NSEI`

**Returns:** `dict[symbol → pd.DataFrame]`  
**Cache TTL:** 1 hour (heavy call — used only in Time Machine tab)

---

### Caching Strategy

| Function | TTL (Market Open) | TTL (Market Closed) |
|----------|-------------------|---------------------|
| `fetch_ticker` | 60s | 5 min |
| `fetch_indices` | 60s | 5 min |
| `fetch_all_stocks_5d` | 60s | 5 min |
| `fetch_all_history` | 1 hour | 1 hour |

All caching is handled by `@st.cache_data` + SQLite. To force a refresh, press **`C`** in the Streamlit app or reboot the server.

---

### NSE Market Hours Detection

```python
is_open, status, label = is_nse_open()
# is_open → bool
# status  → "Open" | "Closed" | "Pre-Market" | "Weekend"
# label   → human-readable last-close string
```

Timezone: **Asia/Kolkata (IST)**  
Trading hours: **09:15 – 15:30 IST, Mon–Fri**

---

## 🤖 ML Prediction Methodology

> ⚠️ Predictions are **statistical estimates**, not financial advice.

The **Scenario Engine** tab uses a **beta-weighted linear impact model** to estimate how macro shocks affect individual stocks.

### How It Works

1. **Beta coefficient** — Each of the 50 stocks has a pre-defined `beta` value (market sensitivity vs Nifty 50).
2. **Scenario shock** — User selects a macro event (e.g. *Rupee drops 5%*, *Oil spikes +20%*). Each event maps to an estimated Nifty % move.
3. **Stock impact formula:**

```
Stock % Change ≈ Nifty % Change × Beta
New Price       = Current Price × (1 + Stock % Change / 100)
P&L Impact      = (New Price − Current Price) × Quantity
```

4. **Assumptions:**
   - Linear relationship between market and stock returns (CAPM-style)
   - Beta values are static (sourced from historical estimates, not live)
   - No non-linear effects, earnings surprises, or liquidity adjustments

### Beta Reference (sample)

| Stock | Beta | Interpretation |
|-------|------|----------------|
| Bajaj Finance | 1.40 | Moves ~1.4× Nifty |
| Nestle India | 0.55 | Defensive, low volatility |
| Tata Motors | 1.45 | High cyclical sensitivity |
| HDFC Bank | 1.10 | Slightly above market |

---

## ⚡ Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect repo `jyotheeswar012-max/nifty50-stock-tracker`, branch `main`, file `app.py`
3. Click **Deploy** — live in ~3 minutes

## 🖥️ Run Locally

```bash
git clone https://github.com/jyotheeswar012-max/nifty50-stock-tracker
cd nifty50-stock-tracker
pip install -r requirements.txt
streamlit run app.py
```

---

## 🧪 Running Tests Locally

```bash
pip install pytest ruff
pytest tests/ -v
```

To run the linter:

```bash
ruff check utils/ tests/ --select E,W,F --ignore E501
```

---

> ⚠️ Educational use only. Not investment advice.
