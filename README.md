# 📈 Nifty 50 Stock Tracker

A Streamlit web app to track Nifty 50 performance and calculate your stock's estimated gain/loss based on index movements.

## 🚀 Features

- **Live Nifty 50 Data** — Candlestick chart with current index value, points change, and % change
- **Stock Gain/Loss Calculator** — Enter your stock price, quantity, and beta to estimate portfolio impact
- **Live Stock Lookup** — Search any NSE stock by symbol and view its price chart
- **Detailed Explanation** — Step-by-step breakdown of how calculations are done

## 🧮 How the Calculator Works

1. Enter the current Nifty 50 value and how many points it moved (positive = gain, negative = loss)
2. Enter your stock's current price, quantity, and **beta** value
3. The app estimates your stock's % change using: `Stock % Change = Nifty % Change × Beta`
4. It then calculates your portfolio gain or loss

> **Beta** measures how sensitive a stock is to market (Nifty) movements:
> - Beta = 1.0 → Stock moves same as Nifty
> - Beta > 1.0 → More volatile than Nifty (e.g., small-cap stocks)
> - Beta < 1.0 → Less volatile than Nifty (e.g., FMCG stocks)

## 🛠️ Tech Stack

- **Frontend & Backend**: [Streamlit](https://streamlit.io)
- **Data**: [yfinance](https://pypi.org/project/yfinance/) (Yahoo Finance)
- **Charts**: [Plotly](https://plotly.com/python/)
- **Language**: Python 3.10+

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/jyotheeswar012-max/nifty50-stock-tracker.git
cd nifty50-stock-tracker

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## ☁️ Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Select this repo → `main` branch → `app.py`
4. Click **Deploy**!

## ⚠️ Disclaimer

This app is for educational purposes only. Stock estimates are based on Beta correlation and are **not financial advice**. Actual stock movements depend on many factors.

---

Built with ❤️ by [Jyotheeswar Reddy](https://github.com/jyotheeswar012-max)
