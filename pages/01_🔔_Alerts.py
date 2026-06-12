"""
Page: Real-Time Price Alerts
Users set price threshold alerts per stock; app checks live price
and shows a banner + plays an audio beep via st.audio hack.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide")

# ---- shared constants (duplicated to keep pages self-contained) ----
NIFTY50_NAMES = [
    "Reliance Industries", "HDFC Bank", "ICICI Bank", "Infosys", "TCS",
    "Bharti Airtel", "ITC", "Kotak Mahindra Bank", "Larsen & Toubro",
    "HCL Technologies", "Axis Bank", "State Bank of India", "Bajaj Finance",
    "Wipro", "Asian Paints", "Maruti Suzuki", "Sun Pharmaceutical",
    "Titan Company", "UltraTech Cement", "ONGC", "NTPC", "Power Grid Corp",
    "Mahindra & Mahindra", "Tata Motors", "Tata Steel", "JSW Steel",
    "Hindalco Industries", "Adani Enterprises", "Adani Ports", "Bajaj Finserv",
    "Bajaj Auto", "Hero MotoCorp", "Cipla", "Dr. Reddy's Labs",
    "Divi's Laboratories", "Eicher Motors", "Grasim Industries",
    "HDFC Life Insurance", "SBI Life Insurance", "IndusInd Bank",
    "Tata Consumer Products", "Britannia Industries", "Nestle India",
    "Hindustan Unilever", "Coal India", "BPCL", "Tech Mahindra",
    "L&T Finance", "Shriram Finance", "Bharat Electronics",
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

# ---- Session state init ----
if "alerts" not in st.session_state:
    st.session_state.alerts = []   # list of dicts

st.title("🔔 Real-Time Price Alerts")
st.markdown("""
Set **above / below** price thresholds for any Nifty 50 stock.
The dashboard checks live prices and fires a visual banner when triggered.
> ⚠️ Alerts are session-based (reset on page refresh). Use the **Watchlist** page for persistence.
""")

# ---- Add alert form ----
st.subheader("➕ Add New Alert")
cols = st.columns([3, 2, 2, 1])
with cols[0]:
    sel_name = st.selectbox("Stock", NIFTY50_NAMES, key="alert_stock")
with cols[1]:
    direction = st.radio("Trigger", ["⬆️ Above", "⬇️ Below"], horizontal=True, key="alert_dir")
with cols[2]:
    threshold = st.number_input("₹ Threshold", min_value=0.01, value=1000.0, step=10.0, key="alert_thresh")
with cols[3]:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Add", use_container_width=True):
        st.session_state.alerts.append({
            "stock":     sel_name,
            "symbol":    NAME_TO_SYM[sel_name],
            "direction": direction,
            "threshold": threshold,
            "triggered": False,
            "added":     datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%H:%M:%S"),
        })
        st.success(f"✅ Alert added for {sel_name} {direction} ₹{threshold:,.2f}")

st.markdown("---")

if not st.session_state.alerts:
    st.info("💡 No alerts set yet. Add one above.")
else:
    st.subheader("📊 Active Alerts")
    auto_refresh = st.toggle("↺ Auto-check every 60s", value=False)
    if auto_refresh:
        import time
        st.caption("⏳ Auto-checking... (disable toggle to stop)")

    rows = []
    fired = []
    for i, alert in enumerate(st.session_state.alerts):
        price = get_live_price(alert["symbol"])
        status = "⏳ Pending"
        if price is not None:
            above = price >= alert["threshold"]
            if alert["direction"] == "⬆️ Above" and above:
                status = f"🔴 TRIGGERED — ₹{price:,.2f}"
                fired.append(alert)
            elif alert["direction"] == "⬇️ Below" and not above:
                status = f"🔴 TRIGGERED — ₹{price:,.2f}"
                fired.append(alert)
            else:
                status = f"🟢 Watching — ₹{price:,.2f}"
        rows.append({
            "#":        i + 1,
            "Stock":    alert["stock"],
            "Trigger":  alert["direction"],
            "Threshold": f"₹{alert['threshold']:,.2f}",
            "Live Price": f"₹{price:,.2f}" if price else "N/A",
            "Status":   status,
            "Added":    alert["added"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if fired:
        for f in fired:
            st.error(f"🚨 ALERT FIRED: **{f['stock']}** {f['direction']} ₹{f['threshold']:,.2f}!")
        st.snow()

    col_del, col_clr = st.columns([1, 5])
    with col_del:
        del_idx = st.number_input("Delete alert #", min_value=1,
            max_value=max(len(st.session_state.alerts), 1), step=1, value=1)
        if st.button("🗑️ Delete"):
            if 1 <= del_idx <= len(st.session_state.alerts):
                removed = st.session_state.alerts.pop(del_idx - 1)
                st.success(f"Removed alert for {removed['stock']}")
                st.rerun()
    with col_clr:
        if st.button("🧹 Clear All Alerts", type="secondary"):
            st.session_state.alerts = []
            st.rerun()

    if auto_refresh:
        import time
        time.sleep(60)
        st.rerun()
