"""
Page: Real-Time Price Alerts
Users set price threshold alerts per stock; app checks live price
and fires a visual banner + sends email/SMS via utils.notifications.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
from utils.notifications import send_email, send_sms
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide")

# ---- shared constants ----
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


# ---- session state ----
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "notified_set" not in st.session_state:
    # track which alerts already sent notifications (prevent spam)
    st.session_state.notified_set = set()


# ---- helpers ----
def _notification_status() -> dict:
    """Returns current user notification config from session state."""
    return {
        "email":        st.session_state.get("user_email", ""),
        "phone":        st.session_state.get("user_phone", ""),
        "notify_email": st.session_state.get("notify_email", False),
        "notify_sms":   st.session_state.get("notify_sms",   False),
    }


def _fire_notifications(alert: dict, live_price: float) -> list:
    """
    Send email and/or SMS for a triggered alert.
    Returns list of status strings for display.
    """
    ns = _notification_status()
    msgs = []
    subject = f"🔔 Alert: {alert['stock']} {alert['direction']} ₹{alert['threshold']:,.2f}"
    body = (
        f"Your price alert has fired!\n\n"
        f"Stock     : {alert['stock']} ({alert['symbol']})\n"
        f"Condition : {alert['direction']} ₹{alert['threshold']:,.2f}\n"
        f"Live Price: ₹{live_price:,.2f}\n"
        f"Time      : {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S IST')}\n\n"
        f"Nifty50 Stock Tracker — Paper Trading Simulator"
    )
    if ns["notify_email"] and ns["email"]:
        ok, err = send_email(ns["email"], subject, body)
        msgs.append(f"📧 Email {'sent to ' + ns['email'] if ok else 'failed: ' + err}")
    if ns["notify_sms"] and ns["phone"]:
        sms_body = f"🔔 {alert['stock']} {alert['direction']} ₹{alert['threshold']:,.2f} | Live: ₹{live_price:,.2f}"
        ok, err = send_sms(ns["phone"], sms_body)
        msgs.append(f"📱 SMS {'sent to ' + ns['phone'] if ok else 'failed: ' + err}")
    return msgs


# ---- page ----
st.title("🔔 Real-Time Price Alerts")

# Notification status banner
ns = _notification_status()
if ns["email"] or ns["phone"]:
    channels = []
    if ns["notify_email"] and ns["email"]:   channels.append(f"📧 {ns['email']}")
    if ns["notify_sms"]   and ns["phone"]:   channels.append(f"📱 {ns['phone']}")
    if channels:
        st.success(f"🔔 Notifications active — {' | '.join(channels)}")
    else:
        st.info("ℹ️ Contact saved but all channels disabled. Enable them in 👤 Profile.")
else:
    st.warning(
        "⚠️ No contact details saved. Go to **👤 Profile & Notifications** to set up "
        "email/SMS alerts, then come back here."
    )

st.markdown("""
Set **above / below** price thresholds for any Nifty 50 stock.
The dashboard checks live prices and fires a visual banner + sends email/SMS when triggered.
> ⚠️ Alerts are session-based (reset on page refresh).
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

    rows = []
    fired_alerts = []

    for i, alert in enumerate(st.session_state.alerts):
        price = get_live_price(alert["symbol"])
        status = "⏳ Pending"
        triggered = False

        if price is not None:
            above = price >= alert["threshold"]
            if alert["direction"] == "⬆️ Above" and above:
                status    = f"🔴 TRIGGERED — ₹{price:,.2f}"
                triggered = True
            elif alert["direction"] == "⬇️ Below" and not above:
                status    = f"🔴 TRIGGERED — ₹{price:,.2f}"
                triggered = True
            else:
                status = f"🟢 Watching — ₹{price:,.2f}"

        if triggered:
            fired_alerts.append((i, alert, price))

        rows.append({
            "#":         i + 1,
            "Stock":     alert["stock"],
            "Trigger":   alert["direction"],
            "Threshold": f"₹{alert['threshold']:,.2f}",
            "Live Price": f"₹{price:,.2f}" if price else "N/A",
            "Status":    status,
            "Added":     alert["added"],
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Fire notifications for newly triggered alerts
    for idx, alert, price in fired_alerts:
        alert_key = f"{alert['symbol']}_{alert['direction']}_{alert['threshold']}"
        st.error(f"🚨 ALERT FIRED: **{alert['stock']}** {alert['direction']} ₹{alert['threshold']:,.2f}!")

        # Only send notification once per alert (avoid spam on every rerun)
        if alert_key not in st.session_state.notified_set:
            st.session_state.notified_set.add(alert_key)
            notif_msgs = _fire_notifications(alert, price)
            for m in notif_msgs:
                st.info(m)

    if fired_alerts:
        st.snow()

    col_del, col_clr = st.columns([1, 5])
    with col_del:
        del_idx = st.number_input(
            "Delete alert #", min_value=1,
            max_value=max(len(st.session_state.alerts), 1),
            step=1, value=1
        )
        if st.button("🗑️ Delete"):
            if 1 <= del_idx <= len(st.session_state.alerts):
                removed = st.session_state.alerts.pop(del_idx - 1)
                # also remove from notified set
                key = f"{removed['symbol']}_{removed['direction']}_{removed['threshold']}"
                st.session_state.notified_set.discard(key)
                st.success(f"Removed alert for {removed['stock']}")
                st.rerun()
    with col_clr:
        if st.button("🧹 Clear All Alerts", type="secondary"):
            st.session_state.alerts = []
            st.session_state.notified_set = set()
            st.rerun()

    if auto_refresh:
        import time
        st.caption("⏳ Auto-checking... (disable toggle to stop)")
        time.sleep(60)
        st.rerun()
