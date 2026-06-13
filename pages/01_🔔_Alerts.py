"""
Page: Price Alerts — guests can see what alerts look like; creating/saving requires login.
"""
import streamlit as st
from utils.supabase_auth import get_current_user, is_guest, login_nudge
from utils.notifications import send_email, send_sms
from utils.db import al_load, al_add, al_delete, al_clear

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide")
user  = get_current_user()
guest = is_guest()

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

st.title("🔔 Price Alerts")
if guest:
    st.caption("👤 Browsing as **Guest** — live prices visible, saving alerts requires login")
else:
    st.caption(f"Signed in as **{user['full_name']}** • Alerts saved to your account")

# ── Live prices preview (everyone sees this) ──────────────────────────────
st.subheader("📊 Current Live Prices")
preview_stock = st.selectbox("Check live price", NIFTY50_NAMES, key="alert_preview")
preview_price = get_live_price(NAME_TO_SYM[preview_stock])
if preview_price:
    st.metric(preview_stock, f"₹{preview_price:,.2f}")
else:
    st.info("Price unavailable")

st.markdown("---")

# ── Create + manage alerts — requires login ───────────────────────────────
st.subheader("🔔 My Alerts")
if guest:
    login_nudge("create and save price alerts")
else:
    if "notified_set" not in st.session_state:
        st.session_state.notified_set = set()

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

    st.markdown("##### ➕ Add New Alert")
    cols = st.columns([3, 2, 2, 1])
    with cols[0]: sel_name  = st.selectbox("Stock", NIFTY50_NAMES, key="alert_stock")
    with cols[1]: direction = st.radio("Trigger", ["⬆️ Above", "⬇️ Below"], horizontal=True)
    with cols[2]: threshold = st.number_input("₹ Threshold", min_value=0.01, value=1000.0, step=10.0)
    with cols[3]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", use_container_width=True):
            ok = al_add(sel_name, NAME_TO_SYM[sel_name], direction, threshold)
            if ok:
                st.success(f"✅ Alert added for {sel_name}")
                st.rerun()
            else:
                st.error("❌ Failed to save alert.")

    alerts = al_load()
    if not alerts:
        st.info("💡 No active alerts. Add one above.")
    else:
        auto_refresh = st.toggle("↺ Auto-check every 60s")
        rows, fired = [], []
        for alert in alerts:
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
            if triggered: fired.append((alert, price))
            rows.append({
                "Stock": alert["stock"], "Trigger": alert["direction"],
                "Threshold": f"₹{alert['threshold']:,.2f}",
                "Live Price": f"₹{price:,.2f}" if price else "N/A",
                "Status": status, "Added": alert["added"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        for alert, price in fired:
            key = f"{alert['symbol']}_{alert['direction']}_{alert['threshold']}"
            st.error(f"🚨 FIRED: **{alert['stock']}** {alert['direction']} ₹{alert['threshold']:,.2f}")
            if key not in st.session_state.notified_set:
                st.session_state.notified_set.add(key)
                for m in _fire(alert, price): st.info(m)
        if fired: st.snow()

        st.markdown("---")
        del_stock = st.selectbox("Delete alert for:", [a["stock"] for a in alerts])
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("🗑️ Delete Selected", type="secondary"):
                target = next((a for a in alerts if a["stock"] == del_stock), None)
                if target and al_delete(target):
                    st.success(f"✅ Deleted alert for {del_stock}")
                    st.rerun()
        with c2:
            if st.button("🧹 Clear All Alerts", type="secondary"):
                al_clear(); st.rerun()

        if auto_refresh:
            import time; time.sleep(60); st.rerun()
