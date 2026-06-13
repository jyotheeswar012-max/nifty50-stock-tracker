"""
Page: ML Predictions — Linear Regression forecast. No login required.
"""
import streamlit as st
from utils.supabase_auth import get_current_user, is_guest

st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")
user  = get_current_user()
guest = is_guest()

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
import warnings
warnings.filterwarnings("ignore")

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

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

@st.cache_data(ttl=3600)
def fetch_history(sym, period="1y"):
    try:
        h = yf.Ticker(sym).history(period=period, auto_adjust=True)
        if h is not None and not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None)
            return h
    except Exception:
        pass
    return pd.DataFrame()

st.title("🤖 ML Price Predictions")
if guest:
    st.caption("👤 Browsing as **Guest** — predictions available to all users")
else:
    st.caption(f"Signed in as **{user['full_name']}**")

st.info("⚠️ These are **educational** Linear Regression forecasts only. Not financial advice.")

if not SKLEARN_OK:
    st.error("❌ `scikit-learn` not installed. Add `scikit-learn` to requirements.txt.")
    st.stop()

# Controls
c1, c2, c3 = st.columns(3)
with c1: sel_stock  = st.selectbox("Stock", NIFTY50_NAMES)
with c2: period     = st.selectbox("Training Data", ["3mo","6mo","1y","2y"], index=2)
with c3: forecast_d = st.slider("Forecast Days", 5, 30, 10)

sym = NAME_TO_SYM[sel_stock]
hist = fetch_history(sym, period)

if hist.empty or len(hist) < 30:
    st.warning("⚠️ Not enough historical data. Try a longer period.")
    st.stop()

# Feature engineering
try:
    df = hist[["Close"]].copy()
    df["Day"]   = np.arange(len(df))
    df["MA5"]   = df["Close"].rolling(5).mean()
    df["MA20"]  = df["Close"].rolling(20).mean()
    df["Ret1"]  = df["Close"].pct_change(1)
    df["Ret5"]  = df["Close"].pct_change(5)
    df = df.dropna()

    feat_cols = ["Day", "MA5", "MA20", "Ret1", "Ret5"]
    X = df[feat_cols].values
    y = df["Close"].values

    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_sc, y)
    score = model.score(X_sc, y)

    # Fitted line
    y_pred = model.predict(X_sc)

    # Forecast
    last_day = int(df["Day"].iloc[-1])
    future_rows = []
    last_closes = list(df["Close"].values[-20:])
    for i in range(1, forecast_d + 1):
        d       = last_day + i
        ma5     = float(np.mean(last_closes[-5:]))  if len(last_closes) >= 5  else float(np.mean(last_closes))
        ma20    = float(np.mean(last_closes[-20:])) if len(last_closes) >= 20 else float(np.mean(last_closes))
        ret1    = (last_closes[-1] - last_closes[-2]) / last_closes[-2] if len(last_closes) >= 2 else 0.0
        ret5    = (last_closes[-1] - last_closes[-6]) / last_closes[-6] if len(last_closes) >= 6 else 0.0
        x_f     = scaler.transform([[d, ma5, ma20, ret1, ret5]])
        p       = float(model.predict(x_f)[0])
        last_closes.append(p)
        future_date = df.index[-1] + timedelta(days=i)
        future_rows.append({"date": future_date, "forecast": round(p, 2)})

    fut_df = pd.DataFrame(future_rows).set_index("date")

    # Metrics
    curr_price  = safe_float(df["Close"].iloc[-1])
    final_price = safe_float(fut_df["forecast"].iloc[-1])
    change_pct  = ((final_price - curr_price) / curr_price * 100) if curr_price else 0.0

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Current Price",    f"₹{curr_price:,.2f}")
    mc2.metric(f"{forecast_d}-Day Forecast", f"₹{final_price:,.2f}",
               delta=f"{change_pct:+.2f}%")
    mc3.metric("Model R²",         f"{score:.3f}")
    mc4.metric("Training Samples", len(df))

    if change_pct > 1:
        st.success(f"🟢 Model suggests **bullish** trend over next {forecast_d} days")
    elif change_pct < -1:
        st.error(f"🔴 Model suggests **bearish** trend over next {forecast_d} days")
    else:
        st.info(f"⚪ Model suggests **sideways** movement over next {forecast_d} days")

    # Chart
    try:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            mode="lines", name="Actual",
            line=dict(color="#00e5ff", width=1.5),
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=y_pred,
            mode="lines", name="Fitted",
            line=dict(color="#ffd600", width=1.5, dash="dot"),
        ))
        fig.add_trace(go.Scatter(
            x=fut_df.index, y=fut_df["forecast"],
            mode="lines+markers", name=f"{forecast_d}-Day Forecast",
            line=dict(color="#00c853", width=2, dash="dash"),
            marker=dict(size=6),
        ))
        fig.add_vline(
            x=df.index[-1].timestamp() * 1000,
            line_dash="dash", line_color="#ff6d00",
            annotation_text="Today",
        )
        fig.update_layout(
            title=f"{sel_stock} — ML Forecast",
            template="plotly_dark", height=480,
            xaxis_title="Date", yaxis_title="Price (₹)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Chart error: {e}")

    # Forecast table
    st.subheader(f"📊 {forecast_d}-Day Forecast Table")
    fut_display = fut_df.copy()
    fut_display.index = fut_display.index.strftime("%Y-%m-%d")
    fut_display["vs Today"] = fut_display["forecast"].apply(
        lambda p: f"{(p - curr_price) / curr_price * 100:+.2f}%" if curr_price else "N/A"
    )
    st.dataframe(fut_display, use_container_width=True)

except Exception as e:
    st.error(f"❌ Prediction failed: {e}")
