import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Nifty 50 Stock Tracker",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .gain { color: #00c853; font-weight: bold; }
    .loss { color: #ff1744; font-weight: bold; }
    .tag-actual {
        background-color: #00c853; color: black;
        padding: 2px 10px; border-radius: 20px;
        font-size: 13px; font-weight: bold;
    }
    .tag-assumed {
        background-color: #ffd600; color: black;
        padding: 2px 10px; border-radius: 20px;
        font-size: 13px; font-weight: bold;
    }
    .stMetric label { color: #9e9e9e !important; }
</style>
""", unsafe_allow_html=True)

st.title("📈 Nifty 50 Stock Tracker")
st.markdown("Track **actual** Nifty 50 data vs **assumed/simulated** scenarios to estimate your stock's gain or loss.")
st.markdown("---")

# =========================================================
# SECTION 1: ACTUAL NIFTY 50 LIVE DATA
# =========================================================
st.header("🟢 Actual Nifty 50 Data")
st.markdown('<span class="tag-actual">LIVE DATA</span> &nbsp; Fetched in real-time from Yahoo Finance (NSE)', unsafe_allow_html=True)
st.markdown("")

@st.cache_data(ttl=300)
def get_nifty_data(period="3mo"):
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period=period)
    return hist

nifty_live_ok = False
try:
    hist = get_nifty_data()
    if hist.empty:
        raise ValueError("Empty data")

    current_price = hist['Close'].iloc[-1]
    prev_price    = hist['Close'].iloc[-2]
    change        = current_price - prev_price
    pct_change    = (change / prev_price) * 100
    high_52w      = hist['High'].max()
    low_52w       = hist['Low'].min()
    nifty_live_ok = True

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Current Value",   f"₹{current_price:,.2f}")
    col2.metric("Points Change",   f"{change:+.2f}")
    col3.metric("% Change",        f"{pct_change:+.2f}%")
    col4.metric("Period High",     f"₹{high_52w:,.2f}")
    col5.metric("Period Low",      f"₹{low_52w:,.2f}")

    # Actual Candlestick Chart
    fig_actual = go.Figure()
    fig_actual.add_trace(go.Candlestick(
        x=hist.index,
        open=hist['Open'], high=hist['High'],
        low=hist['Low'],   close=hist['Close'],
        name="Nifty 50 Actual",
        increasing_line_color="#00c853",
        decreasing_line_color="#ff1744"
    ))
    # 20-day Moving Average on actual data
    hist['MA20'] = hist['Close'].rolling(20).mean()
    fig_actual.add_trace(go.Scatter(
        x=hist.index, y=hist['MA20'],
        mode='lines', name='20-Day MA',
        line=dict(color='#ffd600', width=1.5, dash='dot')
    ))
    fig_actual.update_layout(
        title="📊 Nifty 50 — Actual Price (Last 3 Months)",
        xaxis_title="Date", yaxis_title="Index Value",
        template="plotly_dark", height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig_actual, use_container_width=True)

    # Actual Daily Returns
    hist['Daily_Return_%'] = hist['Close'].pct_change() * 100
    fig_ret = px.bar(
        hist.dropna(), x=hist.dropna().index, y='Daily_Return_%',
        color='Daily_Return_%',
        color_continuous_scale=["#ff1744", "#ffd600", "#00c853"],
        title="📉 Actual Daily Returns (%)",
        template="plotly_dark", height=300,
        labels={"Daily_Return_%": "Return (%)", "index": "Date"}
    )
    st.plotly_chart(fig_ret, use_container_width=True)

except Exception as e:
    st.warning(f"⚠️ Could not fetch live Nifty data: {e}. Using fallback values.")
    current_price = 22500.0
    pct_change    = -0.89
    change        = -200.0

st.markdown("---")

# =========================================================
# SECTION 2: ASSUMED / SIMULATED DATA
# =========================================================
st.header("🟡 Assumed / Simulated Nifty Scenario")
st.markdown('<span class="tag-assumed">SIMULATED</span> &nbsp; You define the assumed movement — app calculates impact', unsafe_allow_html=True)
st.markdown("")

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("📊 Set Assumed Nifty Movement")
    assumed_base   = st.number_input("Assumed Base Nifty Value", value=float(round(current_price if nifty_live_ok else 22500.0, 2)), step=50.0)
    assumed_change = st.number_input("Assumed Change in Points (+ gain / − loss)", value=-200.0, step=10.0)
    assumed_new    = assumed_base + assumed_change
    assumed_pct    = (assumed_change / assumed_base) * 100

    # Real vs Assumed comparison
    st.markdown("#### 🔍 Actual vs Assumed")
    compare_df = pd.DataFrame({
        "Metric":        ["Base Value", "Change (pts)", "Change (%)", "New Value"],
        "🟢 Actual":     [
            f"₹{current_price:,.2f}" if nifty_live_ok else "N/A",
            f"{change:+.2f}"         if nifty_live_ok else "N/A",
            f"{pct_change:+.2f}%"    if nifty_live_ok else "N/A",
            f"₹{current_price:,.2f}" if nifty_live_ok else "N/A"
        ],
        "🟡 Assumed":    [
            f"₹{assumed_base:,.2f}",
            f"{assumed_change:+.2f}",
            f"{assumed_pct:+.2f}%",
            f"₹{assumed_new:,.2f}"
        ]
    })
    st.dataframe(compare_df, use_container_width=True, hide_index=True)

with col_r:
    st.subheader("💼 Your Stock Details")
    stock_name  = st.text_input("Stock Name", value="Reliance")
    stock_price = st.number_input("Stock Current Price (₹)", value=2500.0, step=10.0)
    quantity    = st.number_input("Quantity (Shares)", value=10, step=1)
    beta        = st.slider(
        "Beta (Market Sensitivity)", 0.0, 3.0, 1.0, 0.1,
        help="Beta=1: moves with Nifty | >1: more volatile | <1: less volatile"
    )
    st.caption("💡 Common betas: Reliance ~0.9 | HDFC Bank ~1.1 | TCS ~0.7 | Zomato ~1.5")

st.markdown("---")

# =========================================================
# SECTION 3: IMPACT ANALYSIS — ACTUAL vs ASSUMED
# =========================================================
st.header("📉 Impact on Your Stock — Actual vs Assumed")

def calc_impact(nifty_pct, stock_price, quantity, beta):
    stock_pct   = nifty_pct * beta
    price_chg   = stock_price * (stock_pct / 100)
    new_price   = stock_price + price_chg
    old_val     = stock_price * quantity
    new_val     = new_price * quantity
    pl          = new_val - old_val
    return stock_pct, price_chg, new_price, old_val, new_val, pl

# Actual impact
if nifty_live_ok:
    a_spct, a_pchg, a_nprice, a_oval, a_nval, a_pl = calc_impact(pct_change, stock_price, quantity, beta)
else:
    a_spct = a_pchg = a_nprice = a_oval = a_nval = a_pl = None

# Assumed impact
s_spct, s_pchg, s_nprice, s_oval, s_nval, s_pl = calc_impact(assumed_pct, stock_price, quantity, beta)

col_a, col_s = st.columns(2)

with col_a:
    st.markdown("### 🟢 Based on Actual Nifty")
    if nifty_live_ok:
        st.metric("Stock % Change", f"{a_spct:+.2f}%")
        st.metric("New Stock Price", f"₹{a_nprice:,.2f}", delta=f"₹{a_pchg:+.2f}")
        st.metric("Portfolio Value", f"₹{a_nval:,.2f}", delta=f"₹{a_pl:+.2f}")
        if a_pl > 0:
            st.success(f"✅ GAIN: ₹{a_pl:,.2f}")
        elif a_pl < 0:
            st.error(f"❌ LOSS: ₹{abs(a_pl):,.2f}")
        else:
            st.info("⚖️ No change")
    else:
        st.warning("Live data unavailable.")

with col_s:
    st.markdown("### 🟡 Based on Assumed Nifty")
    st.metric("Stock % Change", f"{s_spct:+.2f}%")
    st.metric("New Stock Price", f"₹{s_nprice:,.2f}", delta=f"₹{s_pchg:+.2f}")
    st.metric("Portfolio Value", f"₹{s_nval:,.2f}", delta=f"₹{s_pl:+.2f}")
    if s_pl > 0:
        st.success(f"✅ GAIN: ₹{s_pl:,.2f}")
    elif s_pl < 0:
        st.error(f"❌ LOSS: ₹{abs(s_pl):,.2f}")
    else:
        st.info("⚖️ No change")

# Visual Bar Chart: Actual vs Assumed P&L
if nifty_live_ok:
    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(
        x=["Actual P&L", "Assumed P&L"],
        y=[a_pl, s_pl],
        marker_color=["#00c853" if a_pl >= 0 else "#ff1744",
                      "#00c853" if s_pl >= 0 else "#ff1744"],
        text=[f"₹{a_pl:+,.2f}", f"₹{s_pl:+,.2f}"],
        textposition="outside"
    ))
    fig_compare.update_layout(
        title=f"Actual vs Assumed P&L for {stock_name} ({quantity} shares)",
        yaxis_title="Profit / Loss (₹)",
        template="plotly_dark", height=350
    )
    st.plotly_chart(fig_compare, use_container_width=True)

# Scenario Sensitivity Table
st.markdown("#### 📋 Sensitivity Table — What if Nifty moves by...")
scenarios = [-500, -300, -200, -100, 0, 100, 200, 300, 500]
rows = []
for pts in scenarios:
    pct  = (pts / assumed_base) * 100
    spct = pct * beta
    pchg = stock_price * (spct / 100)
    pl_s = pchg * quantity
    rows.append({
        "Nifty Change (pts)": f"{pts:+}",
        "Nifty % Change":     f"{pct:+.2f}%",
        "Stock % Change":     f"{spct:+.2f}%",
        "New Stock Price":    f"₹{stock_price + pchg:,.2f}",
        "P&L (₹)":           f"₹{pl_s:+,.2f}"
    })
sensitivity_df = pd.DataFrame(rows)
st.dataframe(sensitivity_df, use_container_width=True, hide_index=True)

with st.expander("📘 Formula Reference"):
    st.markdown(f"""
    | Formula | Value |
    |---------|-------|
    | Nifty % Change | `points_change / base_value × 100` |
    | Stock % Change | `Nifty % × Beta ({beta})` |
    | New Stock Price | `Current Price × (1 + Stock%/100)` |
    | P&L | `(New Price − Old Price) × Quantity` |

    > ⚠️ **Disclaimer**: Estimates use Beta correlation only. Real stock movement depends on company news, sector, global cues & market sentiment.
    """)

st.markdown("---")

# =========================================================
# SECTION 4: LIVE NSE STOCK LOOKUP
# =========================================================
st.header("🔍 Live NSE Stock Lookup")
col_sym, col_per = st.columns([2, 1])
with col_sym:
    symbol_input = st.text_input("NSE Symbol (e.g., RELIANCE, HDFCBANK, TCS, INFY)", value="RELIANCE")
with col_per:
    period_choice = st.selectbox("Period", ["1wk", "1mo", "3mo", "6mo", "1y"], index=1)

if st.button("🔎 Fetch Stock Data"):
    try:
        ticker = f"{symbol_input.strip().upper()}.NS"
        s = yf.Ticker(ticker)
        sh = s.history(period=period_choice)
        if sh.empty:
            st.error("No data found. Check symbol — use all caps like RELIANCE, HDFCBANK.")
        else:
            lp = sh['Close'].iloc[-1]
            pp = sh['Close'].iloc[-2]
            chg = lp - pp
            pct = (chg / pp) * 100
            c1, c2, c3 = st.columns(3)
            c1.metric("Current Price", f"₹{lp:,.2f}")
            c2.metric("Change",        f"₹{chg:+.2f}")
            c3.metric("% Change",      f"{pct:+.2f}%")

            fig_s = go.Figure()
            fig_s.add_trace(go.Candlestick(
                x=sh.index,
                open=sh['Open'], high=sh['High'],
                low=sh['Low'],   close=sh['Close'],
                name=symbol_input.upper(),
                increasing_line_color="#00c853",
                decreasing_line_color="#ff1744"
            ))
            fig_s.update_layout(
                title=f"{symbol_input.upper()} — Actual Price Chart",
                template="plotly_dark", height=400
            )
            st.plotly_chart(fig_s, use_container_width=True)
    except Exception as ex:
        st.error(f"Error: {ex}")

st.markdown("---")
st.markdown("<center>Built with ❤️ using Streamlit | Live Data: Yahoo Finance (yfinance) | Simulated Data: User-defined</center>", unsafe_allow_html=True)
