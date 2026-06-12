# 📈 NSE & Nifty 50 Stock Tracker

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nifty50-stock-tracker.streamlit.app)

> **Live App → [https://nifty50-stock-tracker.streamlit.app](https://nifty50-stock-tracker.streamlit.app)**

A real-time NSE & Nifty 50 dashboard built with **Streamlit** and **Yahoo Finance (yfinance)**.

---

## 🚀 Features

| Page | Description |
|------|-------------|
| 🏦 NSE Market Overview | Live NSE indices, market open/close status, advance/decline ratio, multi-index trend comparison |
| 📈 Nifty 50 Index | Candlestick chart with MA20 & MA50, daily returns, volume |
| 🏢 All 50 Companies | Live prices for all 50 Nifty stocks with sector filter & sort |
| 🏆 Gainers & Losers | Top N gainers/losers + sector heatmap (treemap) |
| 🧮 P&L Calculator | Actual vs assumed Nifty impact on your stock holdings + sensitivity table |
| 🔍 Stock Chart Lookup | Candlestick / Line / Area chart for any NSE stock + volume |

---

## 🛠️ Tech Stack

- **Python 3.10+**
- [Streamlit](https://streamlit.io) — UI framework
- [yfinance](https://github.com/ranaroussi/yfinance) — Yahoo Finance data
- [Plotly](https://plotly.com/python/) — Interactive charts
- [Pandas](https://pandas.pydata.org/) / [NumPy](https://numpy.org/) — Data processing

---

## ⚡ Deploy on Streamlit Cloud (Free)

1. Fork or clone this repo
2. Go to **[share.streamlit.io](https://share.streamlit.io)**
3. Click **New app**
4. Select your repo, branch `main`, file `app.py`
5. Click **Deploy** — your app goes live in ~2 minutes!

---

## 🖥️ Run Locally

```bash
git clone https://github.com/jyotheeswar012-max/nifty50-stock-tracker
cd nifty50-stock-tracker
pip install -r requirements.txt
streamlit run app.py
```

---

## ⚠️ Disclaimer

This app is for **educational purposes only**. Data sourced from Yahoo Finance. Not investment advice.

---

<p align="center">Built with ❤️ using Streamlit &nbsp;| Data: NSE via Yahoo Finance</p>
