import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide")

from utils.theme import inject, inject_topbar
inject()

try:
    from utils.supabase_auth import get_current_user, logout, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def logout(): pass
    def is_guest(): return True
    def login_nudge(f=""): st.info("💡 Sign in to save your data.")

user = get_current_user()
inject_topbar(user=user)

NIFTY50 = [
    {"symbol":"RELIANCE.NS","name":"Reliance Industries"},{"symbol":"HDFCBANK.NS","name":"HDFC Bank"},
    {"symbol":"ICICIBANK.NS","name":"ICICI Bank"},{"symbol":"INFY.NS","name":"Infosys"},{"symbol":"TCS.NS","name":"TCS"},
    {"symbol":"BHARTIARTL.NS","name":"Bharti Airtel"},{"symbol":"ITC.NS","name":"ITC"},{"symbol":"KOTAKBANK.NS","name":"Kotak Mahindra Bank"},
    {"symbol":"LT.NS","name":"Larsen & Toubro"},{"symbol":"HCLTECH.NS","name":"HCL Technologies"},
    {"symbol":"AXISBANK.NS","name":"Axis Bank"},{"symbol":"SBIN.NS","name":"State Bank of India"},
    {"symbol":"BAJFINANCE.NS","name":"Bajaj Finance"},{"symbol":"WIPRO.NS","name":"Wipro"},
    {"symbol":"ASIANPAINT.NS","name":"Asian Paints"},{"symbol":"MARUTI.NS","name":"Maruti Suzuki"},
    {"symbol":"SUNPHARMA.NS","name":"Sun Pharmaceutical"},{"symbol":"TITAN.NS","name":"Titan Company"},
    {"symbol":"ULTRACEMCO.NS","name":"UltraTech Cement"},{"symbol":"ONGC.NS","name":"ONGC"},
    {"symbol":"NTPC.NS","name":"NTPC"},{"symbol":"POWERGRID.NS","name":"Power Grid Corp"},
    {"symbol":"M&M.NS","name":"Mahindra & Mahindra"},{"symbol":"TATAMOTORS.NS","name":"Tata Motors"},
    {"symbol":"TATASTEEL.NS","name":"Tata Steel"},{"symbol":"JSWSTEEL.NS","name":"JSW Steel"},
    {"symbol":"HINDALCO.NS","name":"Hindalco Industries"},{"symbol":"ADANIENT.NS","name":"Adani Enterprises"},
    {"symbol":"ADANIPORTS.NS","name":"Adani Ports"},{"symbol":"BAJAJFINSV.NS","name":"Bajaj Finserv"},
    {"symbol":"BAJAJAUTO.NS","name":"Bajaj Auto"},{"symbol":"HEROMOTOCO.NS","name":"Hero MotoCorp"},
    {"symbol":"CIPLA.NS","name":"Cipla"},{"symbol":"DRREDDY.NS","name":"Dr. Reddy's Labs"},
    {"symbol":"DIVISLAB.NS","name":"Divi's Laboratories"},{"symbol":"EICHERMOT.NS","name":"Eicher Motors"},
    {"symbol":"GRASIM.NS","name":"Grasim Industries"},{"symbol":"HDFCLIFE.NS","name":"HDFC Life Insurance"},
    {"symbol":"SBILIFE.NS","name":"SBI Life Insurance"},{"symbol":"INDUSINDBK.NS","name":"IndusInd Bank"},
    {"symbol":"TATACONSUM.NS","name":"Tata Consumer Products"},{"symbol":"BRITANNIA.NS","name":"Britannia Industries"},
    {"symbol":"NESTLEIND.NS","name":"Nestle India"},{"symbol":"HINDUNILVR.NS","name":"Hindustan Unilever"},
    {"symbol":"COALINDIA.NS","name":"Coal India"},{"symbol":"BPCL.NS","name":"BPCL"},
    {"symbol":"TECHM.NS","name":"Tech Mahindra"},{"symbol":"LTF.NS","name":"L&T Finance"},
    {"symbol":"SHRIRAMFIN.NS","name":"Shriram Finance"},{"symbol":"BEL.NS","name":"Bharat Electronics"},
]
N2S = {s["name"]: s["symbol"] for s in NIFTY50}
NAMES = [s["name"] for s in NIFTY50]
IST = pytz.timezone("Asia/Kolkata")

PLT_LAYOUT = dict(paper_bgcolor="#ffffff",plot_bgcolor="#fafafa",font=dict(color="#1e293b",family="Inter, sans-serif",size=12),title_font=dict(size=15,color="#0f172a"),margin=dict(l=16,r=16,t=48,b=16),legend=dict(font=dict(color="#1e293b",size=12),bgcolor="rgba(255,255,255,0.85)",bordercolor="#e2e8f0",borderwidth=1))
AXIS_STYLE = dict(tickfont=dict(color="#1e293b",size=11),title_font=dict(color="#0f172a",size=12),linecolor="#cbd5e1",gridcolor="#f1f5f9",zerolinecolor="#cbd5e1")

def style_fig(fig):
    fig.update_xaxes(**AXIS_STYLE); fig.update_yaxes(**AXIS_STYLE); return fig

def sf(v, d=0.0):
    try:
        f=float(v); return d if (pd.isna(f) or np.isinf(f)) else f
    except: return d

@st.cache_data(ttl=60)
def get_price(sym):
    for period,interval in [("1d","1m"),("5d",None)]:
        try:
            kw=dict(period=period,auto_adjust=True)
            if interval: kw["interval"]=interval
            h=yf.Ticker(sym).history(**kw)
            if h is not None and not h.empty:
                c=h["Close"]
                if isinstance(c,pd.DataFrame): c=c.iloc[:,0]
                p=sf(c.iloc[-1])
                if p>0: return p
        except: pass
    return None

for k,v in [("alerts",[]), ("alert_history",[])]:
    if k not in st.session_state: st.session_state[k]=v

st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">🔔</div>
  <div>
    <div class="hero-title">Price Alerts</div>
    <div class="hero-sub">
      <span class='ui-badge badge-live'>🟢 Live Monitoring</span>
      &nbsp;&nbsp;Get notified when stocks hit your target price
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if is_guest(): login_nudge("save your alerts permanently")

tab_set, tab_active, tab_hist = st.tabs(["➕  Set Alert", "🔔  Active Alerts", "📜  Alert History"])

with tab_set:
    st.markdown("<p class='sec-label'>➕ Create New Alert</p>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: sel_name = st.selectbox("🏢 Stock", NAMES, key="al_name")
    with c2: al_type  = st.selectbox("📈 Trigger", ["Above (↑)","Below (↓)","Change % (±)"], key="al_type")
    with c3: al_val   = st.number_input("🎯 Target", min_value=0.0, value=0.0, step=0.5, key="al_val")
    with c4:
        lp = get_price(N2S[sel_name])
        if lp: st.metric("Live Price", f"₹{lp:,.2f}")
        else: st.warning("⏳ Unavailable")
    al_note = st.text_input("📝 Note (optional)", max_chars=80, key="al_note")
    if st.button("➕ Add Alert", type="primary", key="btn_add_alert"):
        if al_val <= 0: st.error("❌ Target must be > 0")
        else:
            st.session_state.alerts.append({"stock":sel_name,"symbol":N2S[sel_name],"type":al_type,"target":al_val,"note":al_note,"created":datetime.now(IST).strftime("%Y-%m-%d %H:%M"),"status":"Active","current_price":lp or 0})
            st.success(f"✅ Alert set: {sel_name} {al_type} ₹{al_val:,.2f}"); st.rerun()

with tab_active:
    alerts = st.session_state.alerts
    active = [a for a in alerts if a["status"]=="Active"]
    if not active: st.info("💡 No active alerts. Create one in the 'Set Alert' tab.")
    else:
        st.markdown(f"<p class='sec-label'>🔔 {len(active)} Active Alert(s)</p>",unsafe_allow_html=True)
        triggered = []
        for i,a in enumerate(active):
            cp=get_price(a["symbol"]) or a["current_price"]; a["current_price"]=cp
            trig=False
            if a["type"]=="Above (↑)" and cp>=a["target"]: trig=True
            elif a["type"]=="Below (↓)" and cp<=a["target"]: trig=True
            elif a["type"]=="Change % (±)":
                ref=a.get("ref_price",cp)
                if abs((cp-ref)/ref*100)>=a["target"]: trig=True
            diff=cp-a["target"]; pct=diff/a["target"]*100 if a["target"] else 0
            status="🚨 TRIGGERED" if trig else "🔍 Watching"
            bg="#fff1f2" if trig else "#f0fdf4"
            st.markdown(f"""<div style='background:{bg};border-radius:10px;padding:.8rem 1.2rem;margin-bottom:.5rem;border:1px solid {'#fda4af' if trig else '#86efac'};'>
              <b>{a['stock']}</b> &nbsp;—&nbsp; {a['type']} <b>₹{a['target']:,.2f}</b> &nbsp;|&nbsp;
              Live: <b>₹{cp:,.2f}</b> &nbsp;|&nbsp; Gap: {diff:+,.2f} ({pct:+.2f}%) &nbsp;|&nbsp; {status}
              {'<br><small>📝 '+a['note']+'</small>' if a['note'] else ''}
            </div>""", unsafe_allow_html=True)
            if trig: triggered.append(i)
        if triggered:
            if st.button("✅ Mark Triggered as Done", key="btn_mark_done"):
                for i in triggered:
                    st.session_state.alerts[i]["status"]="Triggered"
                    st.session_state.alert_history.append(st.session_state.alerts[i])
                st.session_state.alerts=[a for a in st.session_state.alerts if a["status"]=="Active"]
                st.rerun()
        if st.button("🗑️ Clear All Alerts", key="btn_clear_alerts"):
            st.session_state.alerts=[]; st.rerun()

with tab_hist:
    hist=st.session_state.alert_history
    if not hist: st.info("💡 No alert history yet.")
    else:
        st.dataframe(pd.DataFrame(hist),use_container_width=True,hide_index=True)
        if st.button("🗑️ Clear History", key="btn_clear_hist"):
            st.session_state.alert_history=[]; st.rerun()
