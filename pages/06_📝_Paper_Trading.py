"""
Page: Paper Trading Simulator  —  light theme
"""
import streamlit as st
from utils.supabase_auth import get_current_user, is_guest, login_nudge
from utils.theme import inject

st.set_page_config(page_title="Paper Trading", page_icon="📝", layout="wide")
inject()

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz
import io
import warnings
warnings.filterwarnings("ignore")

user  = get_current_user()
guest = is_guest()

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
def get_live_price(sym):
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        if h is not None and not h.empty:
            return safe_float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None

for k, v in [("pt_balance", 1_000_000.0), ("pt_holdings", {}),
             ("pt_trades", []), ("pt_equity", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

IST = pytz.timezone("Asia/Kolkata")

def _snapshot_equity():
    port_val = sum(
        (get_live_price(s) or h["avg_price"]) * h["qty"]
        for s, h in st.session_state.pt_holdings.items()
    )
    st.session_state.pt_equity.append({
        "time":   datetime.now(IST).strftime("%H:%M:%S"),
        "equity": round(st.session_state.pt_balance + port_val, 2),
    })

def generate_pdf(user_info):
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Nifty50 Tracker — Paper Trading Report", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Generated: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}", ln=True, align="C")
        pdf.cell(0, 8,
            f"User: {user_info['full_name']} ({user_info['email']})" if user_info else "User: Guest Session",
            ln=True, align="C")
        pdf.ln(4)
        port_val = sum(
            (get_live_price(s) or h["avg_price"]) * h["qty"]
            for s, h in st.session_state.pt_holdings.items()
        )
        total_eq = st.session_state.pt_balance + port_val
        pnl      = total_eq - 1_000_000.0
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, "Account Summary", ln=True)
        pdf.set_font("Helvetica", "", 11)
        for label, val in [
            ("Starting Capital", "Rs.10,00,000.00"),
            ("Cash Balance",     f"Rs.{st.session_state.pt_balance:,.2f}"),
            ("Portfolio Value",  f"Rs.{port_val:,.2f}"),
            ("Total Equity",     f"Rs.{total_eq:,.2f}"),
            ("Net P&L",          f"Rs.{pnl:+,.2f}"),
            ("Total Trades",     str(len(st.session_state.pt_trades))),
        ]:
            pdf.cell(60, 8, label + ":", border=0)
            pdf.cell(0,  8, val, ln=True)
        if st.session_state.pt_trades:
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, "Trade Log", ln=True)
            pdf.set_font("Helvetica", "B", 9)
            headers = ["Time", "Stock", "Type", "Qty", "Price", "Value"]
            widths  = [22, 52, 16, 16, 26, 28]
            for h_lbl, w in zip(headers, widths):
                pdf.cell(w, 7, h_lbl, border=1)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            for tr in st.session_state.pt_trades[-50:]:
                row = [str(tr.get("time","")), str(tr.get("stock",""))[:28],
                       str(tr.get("type","")), str(tr.get("qty","")),
                       f"Rs.{tr.get('price',0):,.2f}", f"Rs.{tr.get('value',0):,.2f}"]
                for cell, w in zip(row, widths):
                    pdf.cell(w, 6, cell, border=1)
                pdf.ln()
        return bytes(pdf.output())
    except Exception:
        return None

# ── Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;">
  <div style="width:52px;height:52px;border-radius:50%;
              background:linear-gradient(135deg,#10b981,#06b6d4);
              display:flex;align-items:center;justify-content:center;
              font-size:1.5rem;color:#fff;box-shadow:0 4px 14px rgba(16,185,129,.35);">
    📝
  </div>
  <div>
    <div class="ui-page-title" style="font-size:1.7rem;">Paper Trading Simulator</div>
    <div class="ui-caption" style="margin:0;">Trade with virtual money — zero risk, real prices</div>
  </div>
</div>
""", unsafe_allow_html=True)

if guest:
    st.markdown("<span class='ui-badge badge-hist'>👤 Guest — session only, sign in to save progress</span>", unsafe_allow_html=True)
    login_nudge("save your paper trading progress")
else:
    st.markdown(f"<span class='ui-badge badge-live'>✅ {user['full_name']} — Virtual ₹10,00,000 capital</span>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Account summary ─────────────────────────────────────────────────────
port_val     = sum(
    (get_live_price(s) or h["avg_price"]) * h["qty"]
    for s, h in