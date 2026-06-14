"""
Page: ML Predictions  —  light theme
"""
import streamlit as st

try:
    st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")
except Exception:
    pass

try:
    from utils.theme import inject
    inject()
except Exception:
    pass

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
import warnings
warnings.filterwarnings("ignore")

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    SK_OK = True
except ImportError:
    SK_OK = False

NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro","HCL Technologies",
    "Axis Bank","State Bank of India","Bajaj Finance","Wipro","Asian Paints",
    "Maruti Suzuki","Sun Pharmaceutical","Titan Company","UltraTech Cement","ONGC",
    "NTPC","Power Grid Corp","Mahindra & Mahindra","Tata Motors","Tata Steel",
    "JSW Steel","Hindalco Industries","Adani Enterprises","Adani Ports","Bajaj Finserv",
]
SYMS = [
    "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS",
    "BHARTIARTL.NS","ITC.NS","KOTAKBANK.NS","LT.NS","HCLTECH.NS",
    "AXISBANK.NS","SBIN.NS","BAJFINANCE.NS","WIPRO.NS","ASIANPAINT.NS",
    "MARUTI.NS","SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS","ONGC.NS",
    "NTPC.NS","POWERGRID.NS","M&M.NS","TATAMOTORS.NS","TATASTEEL.NS",
    "JSWSTEEL.NS","HINDALCO.NS","ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS",
]
N2S = dict(zip(NAMES, SYMS))

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;">
  <div style="width:52px;height:52px;border-radius:50%;
              background:linear-gradient(135deg,#8b5cf6,#6366f1);
              display:flex;align-items:center;justify-content:center;
              font-size:1.5rem;color:#fff;box-shadow:0 4px 14px rgba(139,92,246,.35);">
    🤖
  </div>
  <div>
    <div style="font-size:1.7rem;font-weight:700;">ML Price Predictions</div>
    <div style="font-size:.85rem;color:#64748b;margin:0;">Linear, Polynomial &amp; Random Forest forecasting</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("<span style='background:#f59e0b;color:#fff;padding:2px 10px;border-radius:99px;font-size:.75rem;'>⚠️ Simulated — Educational use only</span>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

if not SK_OK:
    st.error("❌ `scikit-learn` not installed. Add it to requirements.txt and redeploy.")
    st.stop()

c1, c2, c3 = st.columns(3)
with c1: stock   = st.selectbox("🏦 Company",        NAMES,             key="ml_stock")
with c2: period  = st.selectbox("📅 History",        ["6mo","1y","2y"], index=1, key="ml_period")
with c3: horizon = st.slider(  "📆 Forecast days", 5, 30, 10,           key="ml_horizon")

st.markdown("<br>", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load(sym, period):
    try:
        h = yf.Ticker(sym).history(period=period, auto_adjust=True)
        if h is not None and not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
            return h
    except Exception:
        pass
    return pd.DataFrame()

with st.spinner("🔮 Fetching data & training models…"):
    hist = load(N2S[stock], period)

if hist.empty or len(hist) < 30:
    st.warning("⚠️ Not enough data. Try a longer period.")
    st.stop()

try:
    close = hist["Close"].dropna().values
    X     = np.arange(len(close)).reshape(-1, 1)
    y     = close

    # Linear Regression
    lr      = LinearRegression().fit(X, y)

    # Polynomial (degree 2 — safer than 3 for long periods)
    poly    = PolynomialFeatures(degree=2)
    Xp      = poly.fit_transform(X)
    plr     = LinearRegression().fit(Xp, y)

    # Random Forest
    rf      = RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y)

    # Future index
    future_X  = np.arange(len(close), len(close) + horizon).reshape(-1, 1)
    future_Xp = poly.transform(future_X)

    lr_pred   = lr.predict(future_X)
    poly_pred = plr.predict(future_Xp)
    rf_pred   = rf.predict(future_X)

    # Clip polynomial to ±50% of last close to avoid runaway extrapolation
    last_close = float(close[-1])
    clip_lo    = last_close * 0.5
    clip_hi    = last_close * 1.5
    poly_pred  = np.clip(poly_pred, clip_lo, clip_hi)

    last_date = hist.index[-1]
    fut_dates = [last_date + timedelta(days=i + 1) for i in range(horizon)]

    # Metrics
    lr_mae = mean_absolute_error(y, lr.predict(X))
    rf_mae = mean_absolute_error(y, rf.predict(X))
    lr_r2  = r2_score(y, lr.predict(X))
    rf_r2  = r2_score(y, rf.predict(X))

    st.markdown("#### 📊 Model Performance")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Linear MAE",      f"₹{lr_mae:.2f}")
    m2.metric("Random Forest MAE",f"₹{rf_mae:.2f}")
    m3.metric("Linear R²",       f"{lr_r2:.3f}")
    m4.metric("Random Forest R²", f"{rf_r2:.3f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart
    st.markdown(f"#### 🔮 {stock} — {horizon}-Day Forecast")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=close, mode="lines", name="Actual",
        line=dict(color="#1a1a2e", width=2)))
    fig.add_trace(go.Scatter(x=fut_dates, y=lr_pred, mode="lines+markers", name="Linear Reg",
        line=dict(color="#6366f1", width=2, dash="dot"), marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=fut_dates, y=poly_pred, mode="lines+markers", name="Polynomial",
        line=dict(color="#f59e0b", width=2, dash="dash"), marker=dict(size=6)))
    fig.add_trace(go.Scatter(x=fut_dates, y=rf_pred, mode="lines+markers", name="Random Forest",
        line=dict(color="#10b981", width=2), marker=dict(size=6)))
    fig.add_vrect(x0=fut_dates[0], x1=fut_dates[-1],
        fillcolor="rgba(99,102,241,0.06)", line_width=0,
        annotation_text="Forecast Zone", annotation_position="top left")
    fig.update_layout(
        template="plotly_white", height=460,
        paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
        font_color="#1a1a2e",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title="Date", yaxis_title="Price (₹)",
        margin=dict(t=60, b=30))
    st.plotly_chart(fig, use_container_width=True)

    # Forecast table
    st.markdown("#### 📅 Forecast Table")
    fore_df = pd.DataFrame({
        "Date":              [d.strftime("%d %b %Y") for d in fut_dates],
        "Linear (₹)":        [f"₹{v:,.2f}" for v in lr_pred],
        "Polynomial (₹)":    [f"₹{v:,.2f}" for v in poly_pred],
        "Random Forest (₹)": [f"₹{v:,.2f}" for v in rf_pred],
    })
    st.dataframe(fore_df, use_container_width=True, hide_index=True)
    st.caption("⚠️ Statistical projections for educational purposes only — not investment advice.")

except Exception as e:
    st.error(f"❌ Model error: {e}")
