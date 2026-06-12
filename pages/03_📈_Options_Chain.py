"""
Page: Options Chain & Put-Call Ratio
Fetches live NSE options data via yfinance .option_chain()
Displays OI heatmap, PCR, max-pain level.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Options Chain", page_icon="📈", layout="wide")

NIFTY50_NAMES = [
    "Nifty 50 Index","Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro",
    "HCL Technologies","Axis Bank","State Bank of India","Bajaj Finance",
    "Wipro","Asian Paints","Maruti Suzuki","Sun Pharmaceutical",
    "Titan Company","UltraTech Cement","ONGC","NTPC","Tata Motors",
    "Tata Steel","Adani Enterprises","Adani Ports","Bajaj Auto",
    "Cipla","Dr. Reddy's Labs","Hindustan Unilever",
]
NAME_TO_SYM = {
    "Nifty 50 Index":    "^NSEI",
    "Reliance Industries":"RELIANCE.NS",
    "HDFC Bank":         "HDFCBANK.NS",
    "ICICI Bank":        "ICICIBANK.NS",
    "Infosys":           "INFY.NS",
    "TCS":               "TCS.NS",
    "Bharti Airtel":     "BHARTIARTL.NS",
    "ITC":               "ITC.NS",
    "Kotak Mahindra Bank":"KOTAKBANK.NS",
    "Larsen & Toubro":   "LT.NS",
    "HCL Technologies":  "HCLTECH.NS",
    "Axis Bank":         "AXISBANK.NS",
    "State Bank of India":"SBIN.NS",
    "Bajaj Finance":     "BAJFINANCE.NS",
    "Wipro":             "WIPRO.NS",
    "Asian Paints":      "ASIANPAINT.NS",
    "Maruti Suzuki":     "MARUTI.NS",
    "Sun Pharmaceutical":"SUNPHARMA.NS",
    "Titan Company":     "TITAN.NS",
    "UltraTech Cement":  "ULTRACEMCO.NS",
    "ONGC":              "ONGC.NS",
    "NTPC":              "NTPC.NS",
    "Tata Motors":       "TATAMOTORS.NS",
    "Tata Steel":        "TATASTEEL.NS",
    "Adani Enterprises": "ADANIENT.NS",
    "Adani Ports":       "ADANIPORTS.NS",
    "Bajaj Auto":        "BAJAJAUTO.NS",
    "Cipla":             "CIPLA.NS",
    "Dr. Reddy's Labs":  "DRREDDY.NS",
    "Hindustan Unilever":"HINDUNILVR.NS",
}

def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default

@st.cache_data(ttl=300)
def get_option_chain(sym, expiry):
    try:
        tk  = yf.Ticker(sym)
        oc  = tk.option_chain(expiry)
        return oc.calls, oc.puts
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=300)
def get_expiries(sym):
    try:
        return list(yf.Ticker(sym).options)
    except Exception:
        return []

@st.cache_data(ttl=60)
def get_spot(sym):
    try:
        h = yf.Ticker(sym).history(period="1d", interval="1m")
        return safe_float(h["Close"].iloc[-1]) if not h.empty else None
    except Exception:
        return None

# ---- UI ----
st.title("📈 Options Chain & PCR")
st.markdown("""
Live **options chain** with Open Interest heatmap, **Put-Call Ratio (PCR)**,
and **Max Pain** level — key institutional positioning signals.
""")

col1, col2 = st.columns(2)
with col1:
    sel_name = st.selectbox("🏢 Underlying", NIFTY50_NAMES)
with col2:
    sym = NAME_TO_SYM.get(sel_name, "^NSEI")
    expiries = get_expiries(sym)
    if not expiries:
        st.error("❌ No options data available for this symbol via Yahoo Finance.")
        st.stop()
    expiry = st.selectbox("📅 Expiry", expiries)

spot = get_spot(sym)
if spot:
    st.metric("Spot Price", f"₹{spot:,.2f}")

with st.spinner("Fetching options chain..."):
    calls, puts_or_err = get_option_chain(sym, expiry)

if calls is None:
    st.error(f"❌ {puts_or_err}")
    st.stop()
puts = puts_or_err

# ---- Compute PCR ----
total_call_oi = safe_float(calls["openInterest"].sum())
total_put_oi  = safe_float(puts["openInterest"].sum())
pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 0.0

pcr_label = (
    "🔴 Bearish (PCR < 0.7)"   if pcr < 0.7 else
    "🟢 Bullish (PCR > 1.3)"   if pcr > 1.3 else
    "🟡 Neutral (0.7–1.3)"
)

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Call OI", f"{int(total_call_oi):,}")
c2.metric("Total Put OI",  f"{int(total_put_oi):,}")
c3.metric("PCR",           pcr)
c4.metric("Signal",        pcr_label)

# ---- Max Pain ----
try:
    strikes = sorted(set(calls["strike"].tolist()) & set(puts["strike"].tolist()))
    pain = {}
    for k in strikes:
        c_row = calls[calls["strike"] == k]
        p_row = puts[puts["strike"]  == k]
        c_oi  = safe_float(c_row["openInterest"].values[0]) if not c_row.empty else 0
        p_oi  = safe_float(p_row["openInterest"].values[0]) if not p_row.empty else 0
        call_loss = sum(safe_float(calls[calls["strike"]==s]["openInterest"].values[0]) * max(0, s-k)
                        for s in strikes if not calls[calls["strike"]==s].empty)
        put_loss  = sum(safe_float(puts[puts["strike"]==s]["openInterest"].values[0])  * max(0, k-s)
                        for s in strikes if not puts[puts["strike"]==s].empty)
        pain[k] = call_loss + put_loss
    max_pain = min(pain, key=pain.get) if pain else None
    if max_pain:
        st.info(f"🕹️ **Max Pain Strike: ₹{max_pain:,.0f}** — point of maximum option-writer profit at expiry")
except Exception as e:
    st.warning(f"⚠️ Max Pain calc: {e}")
    max_pain = None

st.markdown("---")

# ---- OI Heatmap ----
try:
    oi_df = pd.DataFrame({
        "Strike":   calls["strike"].values,
        "Call OI":  calls["openInterest"].fillna(0).values,
        "Put OI":   puts["openInterest"].fillna(0).values,
    })
    if spot:
        oi_df = oi_df[
            (oi_df["Strike"] >= spot * 0.85) &
            (oi_df["Strike"] <= spot * 1.15)
        ].copy()
    fig_oi = go.Figure()
    fig_oi.add_trace(go.Bar(x=oi_df["Strike"], y=oi_df["Call OI"],
        name="Call OI", marker_color="#00c853"))
    fig_oi.add_trace(go.Bar(x=oi_df["Strike"], y=-oi_df["Put OI"],
        name="Put OI",  marker_color="#ff1744"))
    if spot:
        fig_oi.add_vline(x=spot, line_dash="dash", line_color="#ffd600",
            annotation_text=f"Spot ₹{spot:,.0f}")
    if max_pain:
        fig_oi.add_vline(x=max_pain, line_dash="dot", line_color="#ea80fc",
            annotation_text=f"Max Pain ₹{max_pain:,.0f}")
    fig_oi.update_layout(
        title=f"{sel_name} — OI Heatmap ({expiry})",
        template="plotly_dark", barmode="relative", height=450,
        xaxis_title="Strike", yaxis_title="Open Interest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_oi, use_container_width=True)
except Exception as e:
    st.warning(f"⚠️ OI chart: {e}")

# ---- Raw tables ----
tab1, tab2 = st.tabs(["🟢 Calls", "🔴 Puts"])
COLS = ["strike","lastPrice","bid","ask","volume","openInterest","impliedVolatility"]
with tab1:
    st.dataframe(calls[[c for c in COLS if c in calls.columns]]
        .sort_values("strike").reset_index(drop=True),
        use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(puts[[c for c in COLS if c in puts.columns]]
        .sort_values("strike").reset_index(drop=True),
        use_container_width=True, hide_index=True)
