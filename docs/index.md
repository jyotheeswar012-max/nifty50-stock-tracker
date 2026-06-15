# Nifty 50 Tracker

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-red?logo=streamlit)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-pytest-yellow)](testing.md)

**A real-time NSE & Nifty 50 market tracker built with Streamlit, powered by yfinance.**

[Live App](https://nifty50-stock-tracker.streamlit.app){ .md-button .md-button--primary }
[View on GitHub](https://github.com/jyotheeswar012-max/nifty50-stock-tracker){ .md-button }

</div>

---

## What is this?

The **Nifty 50 Tracker** is an interactive web application that provides a real-time window into the National Stock Exchange (NSE) of India. It tracks all 50 constituent stocks of the Nifty 50 index, NSE sectoral indices, and gives users tools to calculate portfolio P&L, explore historical snapshots, and visualize market trends.

## Key Features

| Feature | Description |
|---|---|
| **Market Overview** | Live snapshot of NSE indices — Nifty 50, Bank Nifty, Nifty IT, and more |
| **Nifty 50 Index** | Candlestick / Line / Area chart with configurable time periods (1m–5y) |
| **All 50 Companies** | Live prices, 1-day change %, sector filter, and percentage-change bar chart |
| **Gainers & Losers** | Top N movers with visual comparison chart |
| **P&L Calculator** | Profit/loss + beta-adjusted market impact simulation |
| **Stock Chart** | Per-stock deep-dive with OHLCV chart for any Nifty 50 constituent |
| **Time Machine** | Travel to any historical NSE trading date (includes famous market events) |

## Architecture Overview

```
nifty50-stock-tracker/
├── app.py               # Streamlit entry point — UI orchestration only
├── pages/               # Additional Streamlit pages
├── utils/
│   ├── data.py          # Data fetching (yfinance, NSE)
│   ├── calculations.py  # P&L, beta impact, stock row building
│   ├── charts.py        # Plotly chart builders
│   ├── constants.py     # Nifty 50 tickers, index config, cache TTLs
│   ├── theme.py         # Custom CSS injection
│   └── supabase_auth.py # Optional authentication
├── tests/               # Pytest test suite
├── docs/                # This documentation site
└── mkdocs.yml           # MkDocs configuration
```

## Quick Start

```bash
git clone https://github.com/jyotheeswar012-max/nifty50-stock-tracker.git
cd nifty50-stock-tracker
pip install -r requirements.txt
streamlit run app.py
```

See the [Installation Guide](getting-started/installation.md) for full setup instructions.
