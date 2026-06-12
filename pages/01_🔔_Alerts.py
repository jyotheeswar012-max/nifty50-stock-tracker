"""
Page: Real-Time Price Alerts — gated behind require_login()
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
from utils.supabase_auth import require_login
from utils.notifications import send_email, send_sms
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide")
user = require_login()

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

if "alerts" not in st.session_state:       st.session_state.alerts = []
if "notified_set" not in st.session_state: st.session_state.notified_set = set()

def _ns():
    return {
        "email":        st.session_state.get("user_email", ""),
        "phone":        st.session_state.get("user_phone", ""),
        "notify_email": st.session_state.get("notify_email", False),
        "notify_sms":   st.session_state.get("notify_sms",   False),
    }

def _fire(alert, price):
    ns = _ns()
    subject = f"🔔 Alert: {alert['stock']} {alert['direction']} ₹{alert['threshold']:,.2f}"
    body = (
        f"Stock: {alert['stock']} ({alert['symbol']})\n"
        f"Condition: {alert['direction']} ₹{alert['threshold']:,.2f}\n"
        f"Live Price: ₹{price:,.2f}\n"
        f"Time: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')}"
    )
    msgs = []
    if ns["notify_email"] and ns["email"]:
        ok, err = send_email(ns["email"], subject, body)
        msgs.append(f"📧 Email {'sent' if ok else 'failed: '+err}")
    if ns["notify_sms"] and ns["phone"]:
        ok, err = send_sms(ns["phone"], f"🔔 {alert['stock']} {alert['direction']} ₹{alert['threshold']:,.2f} | Live: ₹{price:,.2f}")
        msgs.append(f"📱 SMS {'sent' if ok else 'failed: '+err}")
    return msgs

st.title("🔔 Real-Time Price Alerts")
st.caption(f"Signed in as **{user['full_name']}**")

ns = _ns()
if ns["email"] or ns["phone"]:
    ch = []
    if ns["notify_email"] and ns["email"]: ch.append(f"📧 {ns['email']}")
    if ns["notify_sms"]   and ns["phone"]: ch.append(f"📱 {ns['phone']}")
    st.success(f"🔔 Notifications active — {' | '.join(ch)}") if ch else st.info("ℹ️ Channels disabled. Enable in 👤 Profile.")
else:
    st.warning("⚠️ No contact saved. Go to 👤 Profile & Notifications to set up alerts.")

st.markdown("---")
st.subheader("➕ Add New Alert")
cols = st.columns([3, 2, 2, 1])
with cols[0]: sel_name  = st.selectbox("Stock", NIFTY50_NAMES, key="alert_stock")
with cols[1]: direction = st.radio("Trigger", ["⬆️ Above", "⬇️ Below"], horizontal=True)
with cols[2]: threshold = st.number_input("₹ Threshold", min_value=0.01, value=1000.0, step=10.0)
with cols[3]:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Add", use_container_width=True):
        st.session_state.alerts.append({
            "stock": sel_name, "symbol": NAME_TO_SYM[sel_name],
            "direction": direction, "threshold": threshold,
            "added": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%H:%M:%S"),
        })
        st.success(f"✅ Alert added for {sel_name}")

st.markdown("---")
if not st.session_state.alerts:
    st.info("💡 No alerts yet.")
else:
    st.subheader("📊 Active Alerts")
    auto_refresh = st.toggle("↺ Auto-check every 60s")
    rows, fired = [], []
    for i, alert in enumerate(st.session_state.alerts):
        price = get_live_price(alert["symbol"])
        triggered = False
        if price is not None:
            above = price >= alert["threshold"]
            if (alert["direction"] == "⬆️ Above" and above) or (alert["direction"] == "⬇️ Below" and not above):
                status = f"🔴 TRIGGERED — ₹{price:,.2f}"; triggered = True
            else:
                status = f"🟢 Watching — ₹{price:,.2f}"
        else:
            status = "⏳ Pending"
        if triggered: fired.append((i, alert, price))
        rows.append({"#": i+1, "Stock": alert["stock"], "Trigger": alert["direction"],
            "Threshold": f"₹{alert['threshold']:,.2f}",
            "Live Price": f"₹{price:,.2f}" if price else "N/A",
            "Status": status, "Added": alert["added"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    for idx, alert, price in fired:
        key = f"{alert['symbol']}_{alert['direction']}_{alert['threshold']}"
        st.error(f"🚨 FIRED: **{alert['stock']}** {alert['direction']} ₹{alert['threshold']:,.2f}")
        if key not in st.session_state.notified_set:
            st.session_state.notified_set.add(key)
            for m in _fire(alert, price): st.info(m)
    if fired: st.snow()

    c1, c2 = st.columns([1, 5])
    with c1:
        di = st.number_input("Delete #", min_value=1, max_value=max(len(st.session_state.alerts),1), step=1, value=1)
        if st.button("🗑️ Delete"):
            r = st.session_state.alerts.pop(di-1)
            st.session_state.notified_set.discard(f"{r['symbol']}_{r['direction']}_{r['threshold']}")
            st.rerun()
    with c2:
        if st.button("🧹 Clear All", type="secondary"):
            st.session_state.alerts = []; st.session_state.notified_set = set(); st.rerun()

    if auto_refresh:
        import time; time.sleep(60); st.rerun()
