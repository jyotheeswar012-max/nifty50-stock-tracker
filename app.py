import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Nifty 50 Stock Tracker",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #2d3250);
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        border: 1px solid #3a3f5c;
    }
    .gain { color: #00c853; font-weight: bold; }
    .loss { color: #ff1744; font-weight: bold; }
    .neutral { color: #ffd600; font-weight: bold; }
    h1 { color: #e0e0e0; }
    .stMetric label { color: #9e9e9e !important; }
</style>
""", unsafe_allow_html=True)

# Title
st.title("📈 Nifty 50 Stock Tracker")
st.markdown("Track Nifty 50 performance and calculate your stock's gain/loss based on index movements.")
st.markdown("---")

# ---- SECTION 1: Live Nifty 50 Data ----
st.header("🏦 Live Nifty 50 Index")

@st.cache_data(ttl=300)
def get_nifty_data(period="1mo"):
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period=period)
    info = nifty.fast_info
    return hist, info

try:
    hist, info = get_nifty_data()
    current_price = hist['Close'].iloc[-1]
    prev_price = hist['Close'].iloc[-2]
    change = current_price - prev_price
    pct_change = (change / prev_price) * 100

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nifty 50 Current", f"₹{current_price:,.2f}")
    with col2:
        st.metric("Points Change", f"{change:+.2f}")
    with col3:
        st.metric("% Change", f"{pct_change:+.2f}%")
    with col4:
        st.metric("Previous Close", f"₹{prev_price:,.2f}")

    # Nifty Chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist['Open'],
        high=hist['High'],
        low=hist['Low'],
        close=hist['Close'],
        name='Nifty 50'
    ))
    fig.update_layout(
        title="Nifty 50 - Last 1 Month",
        xaxis_title="Date",
        yaxis_title="Index Value",
        template="plotly_dark",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.warning(f"Could not fetch live Nifty 50 data. Using demo values. Error: {e}")
    current_price = 22500.0
    pct_change = -0.89

st.markdown("---")

# ---- SECTION 2: Calculator ----
st.header("🧮 Stock Gain/Loss Calculator")
st.markdown("Enter your stock details and simulate how a Nifty 50 movement affects your portfolio.")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Nifty 50 Movement")
    nifty_current = st.number_input("Current Nifty 50 Value", value=float(round(current_price, 2)), step=10.0)
    nifty_change_points = st.number_input("Nifty 50 Change (Points, use - for loss)", value=-200.0, step=10.0)
    nifty_new = nifty_current + nifty_change_points
    nifty_pct = (nifty_change_points / nifty_current) * 100

    st.info(f"📌 Nifty % Change: **{nifty_pct:+.2f}%** → New Value: **{nifty_new:,.2f}**")

with col_right:
    st.subheader("💼 Your Stock Details")
    stock_name = st.text_input("Stock Name (e.g., Reliance, HDFC Bank)", value="Reliance")
    stock_price = st.number_input("Your Stock's Current Price (₹)", value=2500.0, step=10.0)
    quantity = st.number_input("Quantity (Number of Shares)", value=10, step=1)
    beta = st.slider("Beta (Sensitivity to Nifty)", min_value=0.0, max_value=3.0, value=1.0, step=0.1,
                     help="Beta = 1 means stock moves same as Nifty. Beta > 1 = more volatile. Beta < 1 = less volatile.")

st.markdown("---")

# ---- SECTION 3: Results ----
st.header("📉 Impact Analysis")

estimated_stock_change_pct = nifty_pct * beta
estimated_stock_change_price = stock_price * (estimated_stock_change_pct / 100)
new_stock_price = stock_price + estimated_stock_change_price

current_value = stock_price * quantity
new_value = new_stock_price * quantity
pl = new_value - current_value

col1, col2, col3, col4 = st.columns(4)
with col1:
    color = "normal" if pl >= 0 else "inverse"
    st.metric("Stock % Change (Est.)", f"{estimated_stock_change_pct:+.2f}%", delta=f"{estimated_stock_change_pct:+.2f}%")
with col2:
    st.metric("New Stock Price (Est.)", f"₹{new_stock_price:,.2f}", delta=f"₹{estimated_stock_change_price:+.2f}")
with col3:
    st.metric("Portfolio Value Before", f"₹{current_value:,.2f}")
with col4:
    st.metric("Portfolio Value After", f"₹{new_value:,.2f}", delta=f"₹{pl:+.2f}")

# P&L Display
if pl > 0:
    st.success(f"✅ Estimated GAIN: ₹{pl:,.2f} on {quantity} shares of {stock_name}")
elif pl < 0:
    st.error(f"❌ Estimated LOSS: ₹{abs(pl):,.2f} on {quantity} shares of {stock_name}")
else:
    st.info("⚖️ No change estimated.")

# Explanation
with st.expander("📘 How is this calculated?"):
    st.markdown(f"""
    - **Nifty % Change** = `({nifty_change_points:+.0f} / {nifty_current:,.0f}) × 100` = `{nifty_pct:+.2f}%`
    - **Stock % Change (Est.)** = `Nifty % × Beta` = `{nifty_pct:+.2f}% × {beta}` = `{estimated_stock_change_pct:+.2f}%`
    - **New Stock Price** = `{stock_price} + ({stock_price} × {estimated_stock_change_pct/100:.4f})` = `₹{new_stock_price:,.2f}`
    - **P&L** = `(New Price - Old Price) × Quantity` = `₹{estimated_stock_change_price:+.2f} × {quantity}` = `₹{pl:+.2f}`
    
    > ⚠️ **Disclaimer**: This is a simplified estimation using Beta correlation. Actual stock movement depends on many other factors like company news, sector trends, and market sentiment.
    """)

st.markdown("---")

# ---- SECTION 4: Live Stock Lookup ----
st.header("🔍 Live Stock Lookup (NSE)")
st.markdown("Enter any NSE stock symbol to see its current price and chart.")

col_sym, col_period = st.columns([2,1])
with col_sym:
    symbol_input = st.text_input("NSE Stock Symbol (e.g., RELIANCE, HDFCBANK, TCS)", value="RELIANCE")
with col_period:
    period_choice = st.selectbox("Period", ["1wk", "1mo", "3mo", "6mo", "1y"], index=1)

if st.button("🔎 Fetch Stock Data"):
    try:
        ticker_symbol = f"{symbol_input.upper()}.NS"
        stock = yf.Ticker(ticker_symbol)
        stock_hist = stock.history(period=period_choice)

        if stock_hist.empty:
            st.error("No data found. Please check the symbol (e.g., use RELIANCE not Reliance).")
        else:
            latest = stock_hist['Close'].iloc[-1]
            prev = stock_hist['Close'].iloc[-2]
            chg = latest - prev
            pct = (chg / prev) * 100

            c1, c2, c3 = st.columns(3)
            c1.metric("Current Price", f"₹{latest:,.2f}")
            c2.metric("Change", f"₹{chg:+.2f}")
            c3.metric("% Change", f"{pct:+.2f}%")

            fig2 = px.line(
                stock_hist, x=stock_hist.index, y="Close",
                title=f"{symbol_input.upper()} Stock Price",
                template="plotly_dark",
                labels={"Close": "Price (₹)", "index": "Date"}
            )
            fig2.update_traces(line_color="#00e5ff")
            st.plotly_chart(fig2, use_container_width=True)

    except Exception as ex:
        st.error(f"Error fetching data: {ex}")

st.markdown("---")
st.markdown("<center>Built with ❤️ using Streamlit | Data from Yahoo Finance via yfinance</center>", unsafe_allow_html=True)
