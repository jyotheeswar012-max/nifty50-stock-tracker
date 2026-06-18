"""
Page: Watchlist
"""
import streamlit as st
import warnings
warnings.filterwarnings("ignore")

try:
    from utils.supabase_auth import get_current_user, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def is_guest(): return True
    def login_nudge(msg=""): st.info("Sign in to save your data.")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    def inject_topbar(user=None): pass

st.set_page_config(page_title="Watchlist", page_icon="⭐", layout="wide")

import yfinance as yf
import pandas as pd

user  = get_current_user()
guest = is_guest()
try:
    inject_topbar(user=user)
except Exception:
    pass

try:
    from utils.db import wl_load, wl_add, wl_remove
except Exception:
    def wl_load():    return st.session_state.get("watchlist", [])
    def wl_add(s):    st.session_state.setdefault("watchlist",[]).append(s) if s not in st.session_state.get("watchlist",[]) else None; return True
    def wl_remove(s): st.session_state["watchlist"]=[x for x in st.session_state.get("watchlist",[]) if x!=s]; return True

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

@st.cache_data(ttl=120)
def fetch_quote(sym):
    try:
        h = yf.Ticker(sym).history(period="5d", auto_adjust=True)
        if h is not None and len(h)>=2:
            c=float(h["Close"].iloc[-1]); p=float(h["Close"].iloc[-2])
            ch=c-p; pt=(ch/p*100) if p else 0
            return c, ch, pt
    except: pass
    return None, None, None

st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;">
  <div style="width:52px;height:52px;border-radius:50%;
              background:linear-gradient(135deg,#f59e0b,#fbbf24);
              display:flex;align-items:center;justify-content:center;
              font-size:1.5rem;color:#fff;">⭐</div>
  <div>
    <div class="ui-page-title">Watchlist</div>
    <div class="ui-caption">Track your favourite Nifty 50 stocks</div>
  </div>
</div>
""", unsafe_allow_html=True)

cw1, cw2 = st.columns([4,1])
with cw1: add_name = st.selectbox("Stock", NAMES, key="wl_add_sel", label_visibility="collapsed")
with cw2:
    if st.button("➕ Add", type="primary", use_container_width=True, key="wl_add_btn"):
        if guest: login_nudge("save your watchlist")
        else:
            if wl_add(add_name): st.success(f"✅ Added {add_name}"); st.rerun()

watchlist = wl_load()
if not watchlist:
    st.info("💡 Your watchlist is empty. Add stocks above!")
else:
    with st.spinner("Fetching live prices…"):
        rows = []
        for name in watchlist:
            sym = N2S.get(name)
            if not sym: continue
            c, ch, pt = fetch_quote(sym)
            arrow = "⬆️" if (pt or 0) >= 0 else "⬇️"
            rows.append({"Stock": name, "Symbol": sym.replace(".NS",""),
                "Price (₹)": f"₹{c:,.2f}" if c else "N/A",
                "Change (₹)": f"{ch:+.2f}" if ch is not None else "N/A",
                "Change %": f"{arrow} {pt:+.2f}%" if pt is not None else "N/A"})
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    rem = st.selectbox("Remove from watchlist", watchlist, key="wl_rem_sel")
    if st.button("🗑️ Remove", key="wl_rem_btn"):
        if wl_remove(rem): st.success(f"✅ Removed {rem}"); st.rerun()
