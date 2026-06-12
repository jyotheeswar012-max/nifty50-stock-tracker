import streamlit as st
from utils.supabase_auth import require_login

st.set_page_config(page_title="Paper Trading", page_icon="📝", layout="wide")
user = require_login()

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

NIFTY50_NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro","HCL Technologies",
    "Axis Bank","State Bank of India","Bajaj Finance","Wipro","Asian Paints",
    "Maruti Suzuki","Sun Pharmaceutical","Titan Company","UltraTech Cement","ONGC",
    "NTPC","Power Grid Corp","Mahindra & Mahindra","Tata Motors","Tata Steel",
    "JSW Steel","Hindalco Industries","Adani Enterprises","Adani Ports","Bajaj Finserv",
    "Bajaj Auto","Hero MotoCorp","Cipla","Dr. Reddy's Labs","Divi's Laboratories",
    "Eicher Motors","Grasim Industries","HDFC Life Insurance","SBI Life Insurance",
    "IndusInd Bank","Tata Consumer Products","Britannia Industries","Nestle India",
    "Hindustan Unilever","Coal India","BPCL","Tech Mahindra","L&T Finance",
    "Shriram Finance","Bharat Electronics",
]
NIFTY50_SYMS = [
    "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS",
    "BHARTIARTL.NS","ITC.NS","KOTAKBANK.NS","LT.NS","HCLTECH.NS",
    "AXISBANK.NS","SBIN.NS","BAJFINANCE.NS","WIPRO.NS","ASIANPAINT.NS",
    "MARUTI.NS","SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS","ONGC.NS",
    "NTPC.NS","POWERGRID.NS","M&M.NS","TATAMOTORS.NS","TATASTEEL.NS",
    "JSWSTEEL.NS","HINDALCO.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS",
    "BAJAJAUTO.NS","HEROMOTOCO.NS","CIPLA.NS","DRREDDY.NS","DIVISLAB.NS",
    "EICHERMOT.NS","GRASIM.NS","HDFCLIFE.NS","SBILIFE.NS","INDUSINDBK.NS",
    "TATACONSUM.NS","BRITANNIA.NS","NESTLEIND.NS","HINDUNILVR.NS","COALINDIA.NS",
    "BPCL.NS","TECHM.NS","LTF.NS","SHRIRAMFIN.NS","BEL.NS",
]
NAME_TO_SYM = dict(zip(NIFTY50_NAMES, NIFTY50_SYMS))

def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default

@st.cache_data(ttl=60)
def get_live_price(sym):
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty:
            return safe_float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None

# ---- session state ----
if "pt_balance"   not in st.session_state: st.session_state.pt_balance   = 1_000_000.0
if "pt_holdings"  not in st.session_state: st.session_state.pt_holdings  = {}
if "pt_trades"    not in st.session_state: st.session_state.pt_trades    = []
if "pt_equity"    not in st.session_state: st.session_state.pt_equity    = []

IST = pytz.timezone("Asia/Kolkata")

def _snapshot_equity():
    syms = list(st.session_state.pt_holdings.keys())
    prices = {}
    for s in syms:
        p = get_live_price(s)
        if p: prices[s] = p
    port_val = sum(
        prices.get(sym, h["avg_price"]) * h["qty"]
        for sym, h in st.session_state.pt_holdings.items()
    )
    total = st.session_state.pt_balance + port_val
    st.session_state.pt_equity.append({"time": datetime.now(IST).strftime("%H:%M:%S"), "equity": total})

st.title("📝 Paper Trading Simulator")
st.caption(f"Signed in as **{user['full_name']}** • Virtual money only")

# ---- metrics ----
port_val = sum(
    (get_live_price(sym) or h["avg_price"]) * h["qty"]
    for sym, h in st.session_state.pt_holdings.items()
)
total_equity = st.session_state.pt_balance + port_val
m1, m2, m3, m4 = st.columns(4)
m1.metric("💵 Cash Balance",   f"₹{st.session_state.pt_balance:,.2f}")
m2.metric("💼 Portfolio Value", f"₹{port_val:,.2f}")
m3.metric("📊 Total Equity",   f"₹{total_equity:,.2f}")
m4.metric("🔄 Trades",         len(st.session_state.pt_trades))

st.markdown("---")

# ---- order form ----
st.subheader("🛒 Place Order")
col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
with col1: stock_name = st.selectbox("Stock", NIFTY50_NAMES, key="pt_stock")
with col2: order_type = st.radio("Order", ["BUY", "SELL"], horizontal=True)
with col3: qty        = st.number_input("Qty", min_value=1, value=10, step=1)
with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    execute = st.button("⚡ Execute", type="primary", use_container_width=True)

sym = NAME_TO_SYM[stock_name]
live_price = get_live_price(sym)
if live_price:
    st.info(f"📊 Live price of **{stock_name}**: ₹{live_price:,.2f} | Order value: ₹{live_price*qty:,.2f}")

if execute:
    price = live_price or 0.0
    if price <= 0:
        st.error("❌ Could not fetch live price. Try again.")
    elif order_type == "BUY":
        cost = price * qty
        if cost > st.session_state.pt_balance:
            st.error(f"❌ Insufficient balance. Need ₹{cost:,.2f}, have ₹{st.session_state.pt_balance:,.2f}")
        else:
            st.session_state.pt_balance -= cost
            h = st.session_state.pt_holdings.get(sym, {"qty": 0, "avg_price": 0.0})
            total_qty  = h["qty"] + qty
            avg        = (h["avg_price"] * h["qty"] + price * qty) / total_qty
            st.session_state.pt_holdings[sym] = {"qty": total_qty, "avg_price": avg, "name": stock_name}
            st.session_state.pt_trades.append({
                "time": datetime.now(IST).strftime("%H:%M:%S"), "stock": stock_name,
                "type": "BUY", "qty": qty, "price": price, "value": cost,
            })
            _snapshot_equity()
            st.success(f"✅ BUY {qty} x {stock_name} @ ₹{price:,.2f} = ₹{cost:,.2f}")
    else:  # SELL
        holding = st.session_state.pt_holdings.get(sym)
        if not holding or holding["qty"] < qty:
            held = holding["qty"] if holding else 0
            st.error(f"❌ Not enough shares. Holding {held}, trying to sell {qty}.")
        else:
            proceeds     = price * qty
            realised_pnl = (price - holding["avg_price"]) * qty
            st.session_state.pt_balance += proceeds
            new_qty = holding["qty"] - qty
            if new_qty == 0:
                del st.session_state.pt_holdings[sym]
            else:
                st.session_state.pt_holdings[sym]["qty"] = new_qty
            st.session_state.pt_trades.append({
                "time": datetime.now(IST).strftime("%H:%M:%S"), "stock": stock_name,
                "type": "SELL", "qty": qty, "price": price, "value": proceeds,
                "pnl": realised_pnl,
            })
            _snapshot_equity()
            pnl_str = f"₹{realised_pnl:+,.2f}"
            st.success(f"✅ SELL {qty} x {stock_name} @ ₹{price:,.2f} | P&L: {pnl_str}")

st.markdown("---")

# ---- holdings ----
if st.session_state.pt_holdings:
    st.subheader("💼 Current Holdings")
    h_rows = []
    for sym_h, h in st.session_state.pt_holdings.items():
        lp = get_live_price(sym_h) or h["avg_price"]
        pnl = (lp - h["avg_price"]) * h["qty"]
        h_rows.append({
            "Stock": h["name"], "Qty": h["qty"],
            "Avg Price": f"₹{h['avg_price']:,.2f}",
            "Live Price": f"₹{lp:,.2f}",
            "P&L": f"₹{pnl:+,.2f}",
            "📊": "🟢" if pnl >= 0 else "🔴",
        })
    st.dataframe(pd.DataFrame(h_rows), use_container_width=True, hide_index=True)

# ---- trade log ----
if st.session_state.pt_trades:
    st.markdown("---")
    st.subheader("📜 Trade Log")
    st.dataframe(pd.DataFrame(st.session_state.pt_trades), use_container_width=True, hide_index=True)

# ---- reset ----
st.markdown("---")
if st.button("🔄 Reset Paper Trading Account", type="secondary"):
    for k in ["pt_balance","pt_holdings","pt_trades","pt_equity"]:
        del st.session_state[k]
    st.rerun()
