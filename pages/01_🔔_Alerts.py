"""
Page: Price Alerts  —  light theme
"""
import streamlit as st
from utils.supabase_auth import get_current_user, is_guest, login_nudge
from utils.theme import inject

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide")
inject()

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz, warnings
warnings.filterwarnings("ignore")

user  = get_current_user()
guest = is_guest()

try:
    from utils.notifications import send_email, send_sms
except Exception:
    def send_email(*a, **k): return False, "Not configured"
    def send_sms(*a, **k):   return False, "Not configured"

try:
    from utils.db import al_load, al_add, al_delete, al_clear
except Exception:
    def al_load():          return st.session_state.get("alerts", [])
    def al_add(n,s,d,t):    st.session_state.setdefault("alerts",[]).append({"stock_name":n,"symbol":s,"direction":d,"threshold":t,"added":"session","db_id":None}); return True
    def al_delete(a):       st.session_state["alerts"]=[x for x in st.session_state.get("alerts",[]) if x!=a]; return True
    def al_clear():         st.session_state["alerts"]=[]; return True

NAMES = [
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
SYMS = [
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
N2S = dict(zip(NAMES, SYMS))

def safe_float(v, d=0.0):
    try: f=float(v); return d if (np.isnan(f) or np.isinf(f)) else f
    except: return d

@st.cache_data(ttl=60)
def live_price(sym):
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty: return safe_float(h["Close"].iloc[-1])
    except: pass
    return None

# ── Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;">
  <div style="width:52px;height:52px;border-radius:50%;
              background:linear-gradient(135deg,#f59e0b,#ef4444);
              display:flex;align-items:center;justify-content:center;
              font-size:1.5rem;color:#fff;box-shadow:0 4px 14px rgba(245,158,11,.35);">
    🔔
  </div>
  <div>
    <div class="ui-page-title" style="font-size:1.7rem;">Price Alerts</div>
    <div class="ui-caption" style="margin:0;">Get notified when your stocks hit the target</div>
  </div>
</div>
""", unsafe_allow_html=True)

if guest:
    st.markdown("<span class='ui-badge badge-hist'>👤 Guest Mode — live prices visible, saving alerts requires login</span>", unsafe_allow_html=True)
else:
    st.markdown(f"<span class='ui-badge badge-live'>✅ {user['full_name']} — alerts saved to account</span>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Live Price Checker ───────────────────────────────────────────────────
st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
st.markdown("#### 📊 Live Price Check")
col_s, col_p = st.columns([3,2])
with col_s:
    preview = st.selectbox("Select stock", NAMES, key="alert_preview", label_visibility="collapsed")
with col_p:
    price = live_price(N2S[preview])
    if price:
        delta_color = "normal"
        st.metric(preview, f"₹{price:,.2f}")
    else:
        st.info("⏳ Price unavailable right now")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Alerts Management ───────────────────────────────────────────────────
st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
st.markdown("#### 🔔 My Alerts")

if guest:
    login_nudge("create and save price alerts")
else:
    if "notified_set" not in st.session_state:
        st.session_state.notified_set = set()

    IST = pytz.timezone("Asia/Kolkata")

    def _ns():
        return {"email": st.session_state.get("user_email",""),
                "phone": st.session_state.get("user_phone",""),
                "notify_email": st.session_state.get("notify_email", False),
                "notify_sms":   st.session_state.get("notify_sms",   False)}

    def _fire(alert, price):
        ns = _ns()
        label   = alert.get("stock_name") or alert.get("stock","")
        subject = f"🔔 Alert: {label} {alert['direction']} ₹{alert['threshold']:,.2f}"
        body    = (f"Stock: {label} ({alert.get('symbol','')})
"
                   f"Condition: {alert['direction']} ₹{alert['threshold']:,.2f}
"
                   f"Live Price: ₹{price:,.2f}
"
                   f"Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
        msgs = []
        if ns["notify_email"] and ns["email"]:
            ok, err = send_email(ns["email"], subject, body)
            msgs.append(f"📧 Email {'sent' if ok else 'failed: '+err}")
        if ns["notify_sms"] and ns["phone"]:
            ok, err = send_sms(ns["phone"], f"🔔 {label} {alert['direction']} ₹{alert['threshold']:,.2f} | Live: ₹{price:,.2f}")
            msgs.append(f"📱 SMS {'sent' if ok else 'failed: '+err}")
        return msgs

    st.markdown("##### ➕ Add New Alert")
    cols = st.columns([3,2,2,1])
    with cols[0]: sel   = st.selectbox("Stock", NAMES, key="al_stock")
    with cols[1]: dirn  = st.radio("Trigger", ["⬆️ Above", "⬇️ Below"], horizontal=True, key="al_dir")
    with cols[2]: thr   = st.number_input("₹ Threshold", min_value=0.01, value=1000.0, step=10.0, key="al_thr")
    with cols[3]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", use_container_width=True, type="primary"):
            if al_add(sel, N2S[sel], dirn, thr):
                st.success(f"✅ Alert added for {sel}"); st.rerun()
            else:
                st.error("❌ Failed to save alert.")

    alerts = al_load()
    if not alerts:
        st.info("💡 No active alerts. Add one above.")
    else:
        auto_ref = st.toggle("↺ Auto-check every 60s", key="al_auto")
        rows, fired = [], []
        for a in alerts:
            label = a.get("stock_name") or a.get("stock","")
            sym   = a.get("symbol", N2S.get(label,""))
            p     = live_price(sym) if sym else None
            if p is not None:
                met = (a["direction"]=="⬆️ Above" and p>=a["threshold"]) or \
                      (a["direction"]=="⬇️ Below" and p< a["threshold"])
                status = f"🔴 TRIGGERED — ₹{p:,.2f}" if met else f"🟢 Watching — ₹{p:,.2f}"
                if met: fired.append((a, p))
            else:
                status = "⏳ Pending"
            rows.append({"Stock":label,"Trigger":a["direction"],
                         "Threshold":f"₹{a['threshold']:,.2f}",
                         "Live Price":f"₹{p:,.2f}" if p else "N/A",
                         "Status":status, "Added":a.get("added","")})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        for a, p in fired:
            label = a.get("stock_name") or a.get("stock","")
            key   = f"{a.get('symbol','')}_{a['direction']}_{a['threshold']}"
            st.error(f"🚨 FIRED: **{label}** {a['direction']} ₹{a['threshold']:,.2f}")
            if key not in st.session_state.notified_set:
                st.session_state.notified_set.add(key)
                for m in _fire(a, p): st.info(m)
        if fired: st.snow()

        st.markdown("---")
        labels  = [a.get("stock_name") or a.get("stock","") for a in alerts]
        del_stk = st.selectbox("Delete alert for:", labels, key="al_del")
        d1, d2  = st.columns(2)
        with d1:
            if st.button("🗑️ Delete Selected", use_container_width=True):
                target = next((a for a in alerts if (a.get("stock_name") or a.get("stock",""))==del_stk), None)
                if target and al_delete(target):
                    st.success(f"✅ Deleted alert for {del_stk}"); st.rerun()
        with d2:
            if st.button("🧹 Clear All Alerts", use_container_width=True):
                al_clear(); st.rerun()

        if auto_ref:
            import time; time.sleep(60); st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
