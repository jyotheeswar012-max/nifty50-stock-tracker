import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Paper Portfolio", page_icon="💼", layout="wide")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    pass

try:
    from utils.supabase_auth import get_current_user
except Exception:
    def get_current_user(): return None

user = get_current_user()
try:
    inject_topbar(user=user)
except Exception:
    pass

NIFTY50_NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro","HCL Technologies",
    "Axis Bank","State Bank of India","Bajaj Finance","Wipro","Asian Paints",
    "Maruti Suzuki","Sun Pharmaceutical","Titan Company","UltraTech Cement","ONGC",
    "NTPC","Power Grid Corp","Mahindra & Mahindra","Tata Motors","Tata Steel",
    "JSW Steel","Hindalco Industries","Adani Enterprises","Adani Ports","Bajaj Finserv",
]
NIFTY50_SYMS = {
    "Reliance Industries":"RELIANCE.NS","HDFC Bank":"HDFCBANK.NS","ICICI Bank":"ICICIBANK.NS",
    "Infosys":"INFY.NS","TCS":"TCS.NS","Bharti Airtel":"BHARTIARTL.NS","ITC":"ITC.NS",
    "Kotak Mahindra Bank":"KOTAKBANK.NS","Larsen & Toubro":"LT.NS","HCL Technologies":"HCLTECH.NS",
    "Axis Bank":"AXISBANK.NS","State Bank of India":"SBIN.NS","Bajaj Finance":"BAJFINANCE.NS",
    "Wipro":"WIPRO.NS","Asian Paints":"ASIANPAINT.NS","Maruti Suzuki":"MARUTI.NS",
    "Sun Pharmaceutical":"SUNPHARMA.NS","Titan Company":"TITAN.NS","UltraTech Cement":"ULTRACEMCO.NS",
    "ONGC":"ONGC.NS","NTPC":"NTPC.NS","Power Grid Corp":"POWERGRID.NS",
    "Mahindra & Mahindra":"M&M.NS","Tata Motors":"TATAMOTORS.NS","Tata Steel":"TATASTEEL.NS",
    "JSW Steel":"JSWSTEEL.NS","Hindalco Industries":"HINDALCO.NS","Adani Enterprises":"ADANIENT.NS",
    "Adani Ports":"ADANIPORTS.NS","Bajaj Finserv":"BAJAJFINSV.NS",
}

PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a"),
    margin=dict(l=16, r=16, t=48, b=16),
)

st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">💼</div>
  <div>
    <div class="hero-title">Paper Portfolio</div>
    <div class="hero-sub"><span class="ui-badge badge-sim">VIRTUAL</span>&nbsp; Track your virtual holdings with live P&amp;L</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Init portfolio in session state ──
if "pp_holdings" not in st.session_state:
    st.session_state.pp_holdings = []

# ── Add holding form ──
st.markdown("<p class='sec-label'>Add a Holding</p>", unsafe_allow_html=True)
with st.form("pp_add", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
        sel_name = st.selectbox("Stock", NIFTY50_NAMES)
    with c2:
        qty = st.number_input("Qty", min_value=1, value=10, step=1)
    with c3:
        buy_p = st.number_input("Buy Price (₹)", min_value=0.01, value=100.0, step=1.0)
    with c4:
        note = st.text_input("Note", placeholder="Optional…")
    submitted = st.form_submit_button("➕ Add", type="primary")
    if submitted:
        st.session_state.pp_holdings.append({
            "stock": sel_name, "symbol": NIFTY50_SYMS.get(sel_name, ""),
            "qty": qty, "buy_price": buy_p,
            "note": note, "added": datetime.now().strftime("%d %b %Y"),
        })
        st.success(f"✅ Added {qty}× {sel_name} @ ₹{buy_p:.2f}")

if not st.session_state.pp_holdings:
    st.info("📭 No holdings yet. Add a stock above to get started!")
else:
    st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
    st.markdown("<p class='sec-label'>Live Portfolio</p>", unsafe_allow_html=True)

    rows = []
    total_inv = 0.0
    total_cur = 0.0
    to_remove = []

    with st.spinner("Fetching live prices…"):
        for i, h in enumerate(st.session_state.pp_holdings):
            live = h["buy_price"]
            try:
                tick = yf.Ticker(h["symbol"]).history(period="2d", auto_adjust=True)
                if not tick.empty:
                    live = float(tick["Close"].iloc[-1])
            except Exception:
                pass
            inv_val = h["buy_price"] * h["qty"]
            cur_val = live * h["qty"]
            pl = cur_val - inv_val
            pct = (pl / inv_val * 100) if inv_val > 0 else 0
            total_inv += inv_val
            total_cur += cur_val
            rows.append({
                "#": i, "Stock": h["stock"], "Qty": h["qty"],
                "Buy (₹)": round(h["buy_price"], 2),
                "Live (₹)": round(live, 2),
                "Invested (₹)": round(inv_val, 2),
                "Current (₹)": round(cur_val, 2),
                "P&L (₹)": round(pl, 2),
                "Return (%)": round(pct, 2),
                "Added": h["added"],
                "Note": h.get("note", ""),
            })

    total_pl  = total_cur - total_inv
    total_pct = (total_pl / total_inv * 100) if total_inv > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Invested",  f"₹{total_inv:,.2f}")
    m2.metric("Current",   f"₹{total_cur:,.2f}")
    m3.metric("Total P&L", f"₹{total_pl:+,.2f}")
    m4.metric("Return",    f"{total_pct:+.2f}%")

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["#"])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Remove holding
    st.markdown("<p class='sec-label'>Remove a Holding</p>", unsafe_allow_html=True)
    del_name = st.selectbox("Select to remove", [r["Stock"] for r in rows], key="pp_del_sel")
    if st.button("🗑️ Remove", key="pp_del_btn"):
        idx = next((r["#"] for r in rows if r["Stock"] == del_name), None)
        if idx is not None:
            st.session_state.pp_holdings.pop(idx)
            st.success(f"Removed {del_name}")
            st.rerun()

    st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

    # Charts
    if len(rows) > 0:
        df_chart = df[df["P&L (₹)"].notna()].copy()
        c1, c2 = st.columns(2)
        with c1:
            try:
                fig_pl = px.bar(
                    df_chart, x="Stock", y="P&L (₹)",
                    color="P&L (₹)", color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                    color_continuous_midpoint=0, title="P&L per Stock", height=320,
                    text="P&L (₹)",
                )
                fig_pl.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
                fig_pl.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
                st.plotly_chart(fig_pl, use_container_width=True)
            except Exception:
                pass
        with c2:
            try:
                fig_pie = px.pie(
                    df_chart, names="Stock", values="Current (₹)",
                    title="Portfolio Allocation", height=320,
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                )
                fig_pie.update_layout(**PLT_LAYOUT)
                st.plotly_chart(fig_pie, use_container_width=True)
            except Exception:
                pass

    if st.button("🗑️ Clear All Holdings", key="pp_clear"):
        st.session_state.pp_holdings = []
        st.rerun()
