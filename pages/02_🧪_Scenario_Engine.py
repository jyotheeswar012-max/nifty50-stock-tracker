import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Scenario Engine", page_icon="🧪", layout="wide")

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

NIFTY50 = [
    {"symbol":"RELIANCE.NS","name":"Reliance Industries","sector":"Energy","beta":0.90},
    {"symbol":"HDFCBANK.NS","name":"HDFC Bank","sector":"Financial Services","beta":1.10},
    {"symbol":"ICICIBANK.NS","name":"ICICI Bank","sector":"Financial Services","beta":1.20},
    {"symbol":"INFY.NS","name":"Infosys","sector":"IT","beta":0.75},
    {"symbol":"TCS.NS","name":"TCS","sector":"IT","beta":0.70},
    {"symbol":"BHARTIARTL.NS","name":"Bharti Airtel","sector":"Telecom","beta":0.85},
    {"symbol":"ITC.NS","name":"ITC","sector":"FMCG","beta":0.65},
    {"symbol":"KOTAKBANK.NS","name":"Kotak Mahindra Bank","sector":"Financial Services","beta":1.05},
    {"symbol":"LT.NS","name":"Larsen & Toubro","sector":"Construction","beta":1.10},
    {"symbol":"HCLTECH.NS","name":"HCL Technologies","sector":"IT","beta":0.80},
    {"symbol":"AXISBANK.NS","name":"Axis Bank","sector":"Financial Services","beta":1.30},
    {"symbol":"SBIN.NS","name":"State Bank of India","sector":"Financial Services","beta":1.35},
    {"symbol":"BAJFINANCE.NS","name":"Bajaj Finance","sector":"Financial Services","beta":1.40},
    {"symbol":"WIPRO.NS","name":"Wipro","sector":"IT","beta":0.72},
    {"symbol":"ASIANPAINT.NS","name":"Asian Paints","sector":"Consumer Goods","beta":0.60},
    {"symbol":"MARUTI.NS","name":"Maruti Suzuki","sector":"Automobile","beta":0.95},
    {"symbol":"SUNPHARMA.NS","name":"Sun Pharmaceutical","sector":"Pharma","beta":0.70},
    {"symbol":"TITAN.NS","name":"Titan Company","sector":"Consumer Goods","beta":0.90},
    {"symbol":"TATAMOTORS.NS","name":"Tata Motors","sector":"Automobile","beta":1.45},
    {"symbol":"TATASTEEL.NS","name":"Tata Steel","sector":"Metals","beta":1.50},
]

MACRO_EVENTS = {
    "🔴 Rupee depreciates 5%":   {"desc": "USD/INR rises ~5%",         "sectors": {"IT": +3.5, "Energy": -2.0, "Financial Services": -1.5, "Pharma": +2.0}},
    "🟢 Rupee appreciates 3%":   {"desc": "USD/INR falls ~3%",         "sectors": {"IT": -2.0, "Energy": +1.5, "Financial Services": +1.0, "Pharma": -1.5}},
    "🔴 Crude oil spikes +10%":  {"desc": "WTI crude rises ~10%",       "sectors": {"Energy": +4.0, "Automobile": -3.0, "FMCG": -2.5, "Financial Services": -1.5}},
    "🟢 Crude oil crashes -15%": {"desc": "WTI crude falls ~15%",       "sectors": {"Energy": -5.0, "Automobile": +3.5, "FMCG": +3.0, "Financial Services": +2.0}},
    "🟢 RBI rate cut 25bps":     {"desc": "RBI cuts repo rate by 0.25%", "sectors": {"Financial Services": +3.0, "Construction": +2.5, "Automobile": +2.0, "IT": +1.0}},
    "🔴 RBI rate hike 25bps":    {"desc": "RBI hikes repo rate by 0.25%","sectors": {"Financial Services": -2.5, "Construction": -2.0, "Automobile": -1.5, "IT": -0.5}},
    "🔴 Nifty flash crash -5%":  {"desc": "Nifty 50 falls ~5% in week", "sectors": {"Financial Services": -6.0, "IT": -5.0, "Metals": -7.0, "FMCG": -3.0}},
    "🟢 Nifty bull run +5%":     {"desc": "Nifty 50 rises ~5% in week", "sectors": {"Financial Services": +6.0, "IT": +5.0, "Metals": +7.0, "FMCG": +3.0}},
    "🟢 Union Budget — pro-growth":{"desc":"Capital expenditure boost",  "sectors": {"Construction": +5.0, "Defence": +6.0, "Infrastructure": +4.5, "Financial Services": +2.0}},
    "🔴 Global recession fears":  {"desc": "Risk-off selloff",           "sectors": {"IT": -4.0, "Metals": -6.0, "Automobile": -4.5, "FMCG": -1.5}},
}

PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(font=dict(color="#1e293b", size=11), bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#e2e8f0", borderwidth=1),
)

st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">🧪</div>
  <div>
    <div class="hero-title">Scenario Engine</div>
    <div class="hero-sub"><span class="ui-badge badge-sim">SIMULATOR</span>&nbsp; What-if analysis for macro events</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Event selector ──
st.markdown("<p class='sec-label'>Choose a Macro Event</p>", unsafe_allow_html=True)
col1, col2 = st.columns([2, 2])
with col1:
    event_name = st.selectbox("Macro Event", list(MACRO_EVENTS.keys()), label_visibility="collapsed")
event = MACRO_EVENTS[event_name]
with col2:
    custom_move = st.slider("Custom Nifty Move (%)", -20.0, 20.0, 0.0, 0.5, key="se_move",
                            help="Override the event with a custom Nifty % move")

st.info(f"📌 **{event_name}** — {event['desc']}")
st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ── Portfolio builder ──
st.markdown("<p class='sec-label'>Build Your Portfolio</p>", unsafe_allow_html=True)
st.caption("Add stocks and quantities to simulate portfolio impact")

if "se_portfolio" not in st.session_state:
    st.session_state.se_portfolio = [{"stock": "Reliance Industries", "qty": 10, "buy_price": 0.0}]

def add_row():
    st.session_state.se_portfolio.append({"stock": "TCS", "qty": 5, "buy_price": 0.0})

names = [s["name"] for s in NIFTY50]
rows_to_delete = []

for i, row in enumerate(st.session_state.se_portfolio):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 0.4])
    with c1:
        st.session_state.se_portfolio[i]["stock"] = st.selectbox(
            f"Stock #{i+1}", names, index=names.index(row["stock"]) if row["stock"] in names else 0,
            key=f"se_s{i}", label_visibility="collapsed")
    with c2:
        st.session_state.se_portfolio[i]["qty"] = st.number_input(
            "Qty", min_value=1, value=int(row["qty"]), key=f"se_q{i}", label_visibility="collapsed")
    with c3:
        st.session_state.se_portfolio[i]["buy_price"] = st.number_input(
            "Buy ₹", min_value=0.0, value=float(row["buy_price"]), step=1.0,
            key=f"se_bp{i}", label_visibility="collapsed", help="Leave 0 to use live price")
    with c4:
        if st.button("🗑️", key=f"se_del{i}") and len(st.session_state.se_portfolio) > 1:
            rows_to_delete.append(i)

for i in sorted(rows_to_delete, reverse=True):
    st.session_state.se_portfolio.pop(i)

st.button("➕ Add Stock", on_click=add_row, key="se_add")
st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ── Run simulation ──
if st.button("🚀 Run Scenario", type="primary", key="se_run"):
    with st.spinner("Fetching live prices & running simulation…"):
        results = []
        total_old = 0.0
        total_new = 0.0
        for row in st.session_state.se_portfolio:
            meta = next((s for s in NIFTY50 if s["name"] == row["stock"]), None)
            if not meta:
                continue
            # Get live price
            live_price = row["buy_price"]
            if live_price <= 0:
                try:
                    h = yf.Ticker(meta["symbol"]).history(period="2d", auto_adjust=True)
                    if not h.empty:
                        live_price = float(h["Close"].iloc[-1])
                except Exception:
                    live_price = 100.0
            sector = meta["sector"]
            beta = meta["beta"]
            # Sector impact from event
            sector_move = event["sectors"].get(sector, 0.0)
            # If custom move is non-zero, use beta-adjusted custom move
            if custom_move != 0:
                stock_move = custom_move * beta
            else:
                stock_move = sector_move * beta
            new_price = live_price * (1 + stock_move / 100)
            qty = row["qty"]
            old_val = live_price * qty
            new_val = new_price * qty
            pl = new_val - old_val
            total_old += old_val
            total_new += new_val
            results.append({
                "Stock": row["stock"], "Sector": sector, "Beta": beta,
                "Live Price (₹)": round(live_price, 2), "Qty": qty,
                "Sector Move (%)": round(sector_move, 2),
                "Stock Move (%)": round(stock_move, 2),
                "New Price (₹)": round(new_price, 2),
                "Old Value (₹)": round(old_val, 2),
                "New Value (₹)": round(new_val, 2),
                "P&L (₹)": round(pl, 2),
            })

    if results:
        total_pl = total_new - total_old
        total_pct = (total_pl / total_old * 100) if total_old > 0 else 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Portfolio Value (Before)", f"₹{total_old:,.2f}")
        m2.metric("Portfolio Value (After)",  f"₹{total_new:,.2f}")
        m3.metric("Total P&L", f"₹{total_pl:+,.2f}")
        m4.metric("Return", f"{total_pct:+.2f}%")
        if total_pl > 0:
            st.success(f"✅ Scenario gain: ₹{total_pl:,.2f} ({total_pct:+.2f}%)")
        elif total_pl < 0:
            st.error(f"❌ Scenario loss: ₹{abs(total_pl):,.2f} ({total_pct:.2f}%)")
        else:
            st.info("— No change")
        st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)
        try:
            fig = px.bar(df, x="Stock", y="P&L (₹)",
                color="P&L (₹)", color_continuous_scale=["#ef4444","#f59e0b","#10b981"],
                color_continuous_midpoint=0, text="P&L (₹)",
                title=f"P&L per Stock — {event_name}", height=380)
            fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
