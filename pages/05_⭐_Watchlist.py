"""
Page: Watchlist — persisted in Supabase DB
"""
import streamlit as st
from utils.supabase_auth import require_login
from utils.db import wl_load, wl_add, wl_remove

st.set_page_config(page_title="Watchlist", page_icon="⭐", layout="wide")
user = require_login()

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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

st.title("⭐ My Watchlist")
st.caption(f"Signed in as **{user['full_name']}** • Saved to your account")

# ── Load from DB ──────────────────────────────────────────────────
watchlist = wl_load()  # list of {stock_name, symbol, ...}
watched_names = [w["stock_name"] for w in watchlist]

# ── Add stock ─────────────────────────────────────────────────────
available = [s for s in NIFTY50_NAMES if s not in watched_names]
cols = st.columns([3, 1])
with cols[0]:
    add_stock = st.selectbox("Add Stock", available) if available else st.selectbox("Add Stock", ["All stocks added"])
with cols[1]:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Add to Watchlist", use_container_width=True, disabled=not available):
        if wl_add(add_stock, NAME_TO_SYM[add_stock]):
            st.success(f"✅ Added {add_stock}")
            st.rerun()
        else:
            st.error("❌ Could not save. Check Supabase setup.")

if not watchlist:
    st.info("💡 Your watchlist is empty. Add stocks above. Data is saved to your account across sessions!")
else:
    st.markdown("---")
    rows = []
    for w in watchlist:
        name = w["stock_name"]
        sym  = w.get("symbol", NAME_TO_SYM.get(name, ""))
        try:
            h = yf.Ticker(sym).history(period="5d", interval="1d")
            if h is not None and len(h) >= 2:
                curr = safe_float(h["Close"].iloc[-1])
                prev = safe_float(h["Close"].iloc[-2])
                chg  = curr - prev
                pct  = (chg / prev * 100) if prev else 0.0
                rows.append({"Stock": name, "Price (₹)": f"₹{curr:,.2f}",
                    "Change": f"{chg:+.2f}", "Change %": f"{pct:+.2f}%",
                    "📊": "🟢" if chg >= 0 else "🔴"})
            else:
                rows.append({"Stock": name, "Price (₹)": "N/A", "Change": "N/A", "Change %": "N/A", "📊": "?"})
        except Exception:
            rows.append({"Stock": name, "Price (₹)": "N/A", "Change": "N/A", "Change %": "N/A", "📊": "?"})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Remove ────────────────────────────────────────────────────
    st.markdown("---")
    remove = st.selectbox("🗑️ Remove Stock", watched_names)
    if st.button("Remove from Watchlist", type="secondary"):
        if wl_remove(remove):
            st.success(f"✅ Removed {remove}")
            st.rerun()
        else:
            st.error("❌ Could not remove.")
