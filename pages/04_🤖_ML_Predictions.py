"""
Page: ML Price Predictions
Uses scikit-learn Linear Regression + Random Forest on technical features
(RSI, MACD, BB, rolling returns) to predict 5-day forward return direction.
Also shows a simple next-7-day price projection band.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")

NIFTY50_NAMES = [
    "Nifty 50 Index","Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro",
    "HCL Technologies","Axis Bank","State Bank of India","Bajaj Finance",
    "Wipro","Asian Paints","Maruti Suzuki","Sun Pharmaceutical",
    "Titan Company","UltraTech Cement","ONGC","NTPC","Tata Motors",
    "Tata Steel","Adani Enterprises","Adani Ports",
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

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["ret1"]  = d["Close"].pct_change(1)
    d["ret5"]  = d["Close"].pct_change(5)
    d["ret20"] = d["Close"].pct_change(20)
    d["ma10"]  = d["Close"].rolling(10).mean()
    d["ma20"]  = d["Close"].rolling(20).mean()
    d["ma50"]  = d["Close"].rolling(50).mean()
    d["vol10"] = d["ret1"].rolling(10).std()
    # RSI-14
    delta = d["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    d["rsi"] = 100 - 100 / (1 + rs)
    # MACD
    ema12 = d["Close"].ewm(span=12).mean()
    ema26 = d["Close"].ewm(span=26).mean()
    d["macd"]   = ema12 - ema26
    d["signal"] = d["macd"].ewm(span=9).mean()
    d["macd_hist"] = d["macd"] - d["signal"]
    # Bollinger Band position
    bb_mid = d["Close"].rolling(20).mean()
    bb_std = d["Close"].rolling(20).std()
    d["bb_pos"] = (d["Close"] - bb_mid) / bb_std.replace(0, np.nan)
    # Target: did price go up in next 5 days?
    d["future_ret"] = d["Close"].shift(-5).pct_change(5)
    d["target"]     = (d["future_ret"] > 0).astype(int)
    return d

FEATURES = ["ret1","ret5","ret20","vol10","rsi","macd_hist","bb_pos","ma10","ma20","ma50"]

@st.cache_data(ttl=3600)
def load_and_train(sym):
    try:
        h = yf.Ticker(sym).history(period="5y", auto_adjust=True)
        if h is None or len(h) < 100:
            return None
        h.index = pd.to_datetime(h.index).tz_localize(None)
        df = compute_features(h)
        df = df.dropna(subset=FEATURES + ["target"])
        if len(df) < 80:
            return None
        X = df[FEATURES].values
        y = df["target"].values
        sc = StandardScaler()
        X_sc = sc.fit_transform(X)
        X_tr, X_te, y_tr, y_te = train_test_split(X_sc, y, test_size=0.2, shuffle=False)
        rf  = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        rf.fit(X_tr, y_tr)
        acc = accuracy_score(y_te, rf.predict(X_te))
        latest = sc.transform(df[FEATURES].iloc[[-1]].values)
        proba  = rf.predict_proba(latest)[0]
        importances = dict(zip(FEATURES, rf.feature_importances_))
        # Simple linear projection for next 7 days
        last_n = 60
        close_vals = h["Close"].values[-last_n:]
        X_lin = np.arange(last_n).reshape(-1,1)
        lr = LinearRegression().fit(X_lin, close_vals)
        future_X = np.arange(last_n, last_n + 7).reshape(-1,1)
        proj = lr.predict(future_X)
        residuals = close_vals - lr.predict(X_lin)
        sigma = np.std(residuals)
        return {
            "df":          df,
            "history":     h,
            "accuracy":    round(acc * 100, 1),
            "proba_up":    round(proba[1] * 100, 1),
            "proba_dn":    round(proba[0] * 100, 1),
            "importances": importances,
            "proj":        proj,
            "sigma":       sigma,
            "last_date":   h.index[-1],
            "last_close":  safe_float(h["Close"].iloc[-1]),
        }
    except Exception as e:
        return {"error": str(e)}

# ---- UI ----
st.title("🤖 ML Price Predictions")
st.markdown("""
Uses a **Random Forest** classifier trained on 5 years of technical features
(RSI, MACD, Bollinger Band, momentum) to estimate the **5-day forward direction**.
Also shows a simple **linear projection band** for the next 7 trading days.
> ⚠️ This is a **research tool**, not investment advice. Model accuracy is shown transparently.
""")

if not SKLEARN_OK:
    st.error("❌ scikit-learn not installed. Add `scikit-learn` to requirements.txt.")
    st.stop()

col1, col2 = st.columns([3,1])
with col1:
    sel_name = st.selectbox("🏢 Company", NIFTY50_NAMES)
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("🚀 Run Model", type="primary", use_container_width=True)

sym = NAME_TO_SYM.get(sel_name, "^NSEI")

if run or "ml_result" not in st.session_state or st.session_state.get("ml_sym") != sym:
    with st.spinner(f"Training model on 5y of {sel_name} data..."):
        result = load_and_train(sym)
    st.session_state.ml_result = result
    st.session_state.ml_sym    = sym
else:
    result = st.session_state.get("ml_result")

if result is None:
    st.warning("⚠️ Not enough data to train.")
elif "error" in result:
    st.error(f"❌ {result['error']}")
else:
    # Prediction banner
    up   = result["proba_up"]
    dn   = result["proba_dn"]
    acc  = result["accuracy"]
    direction = "🟢 UP" if up > 50 else "🔴 DOWN"
    confidence = max(up, dn)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("5-Day Prediction", direction)
    c2.metric("Up Probability",   f"{up}%")
    c3.metric("Down Probability", f"{dn}%")
    c4.metric("Model Accuracy",   f"{acc}%",
        help="Out-of-sample test accuracy on last 20% of data")

    if confidence >= 65:
        st.success(f"✅ High confidence signal: {direction} ({confidence:.1f}%)")
    elif confidence >= 55:
        st.warning(f"🟡 Moderate signal: {direction} ({confidence:.1f}%) — use with caution")
    else:
        st.info(f"ℹ️ Weak signal: near coin-flip ({confidence:.1f}%) — market is choppy")

    st.markdown("---")

    # 7-day projection chart
    try:
        h    = result["history"]
        proj = result["proj"]
        sigma = result["sigma"]
        last_close = result["last_close"]
        last_date  = result["last_date"]

        # Last 60 actual + 7 projected
        hist_plot = h["Close"].iloc[-60:]
        future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=7, freq="B")
        proj_s = pd.Series(proj, index=future_dates)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_plot.index, y=hist_plot.values,
            mode="lines", name="Actual", line=dict(color="#00e5ff", width=2)))
        fig.add_trace(go.Scatter(x=proj_s.index, y=proj_s.values,
            mode="lines+markers", name="Projection",
            line=dict(color="#ffd600", width=2, dash="dash")))
        fig.add_trace(go.Scatter(
            x=list(proj_s.index) + list(proj_s.index[::-1]),
            y=list(proj_s.values + sigma) + list((proj_s.values - sigma)[::-1]),
            fill="toself", fillcolor="rgba(255,214,0,0.15)",
            line=dict(color="rgba(0,0,0,0)"), name="±1σ Band"))
        fig.add_hline(y=last_close, line_dash="dot", line_color="#9e9e9e",
            annotation_text=f"Current ₹{last_close:,.2f}")
        fig.update_layout(
            title=f"{sel_name} — 7-Day Linear Projection",
            template="plotly_dark", height=420,
            xaxis_title="Date", yaxis_title="Price (₹)",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Projection chart: {e}")

    # Feature importance
    st.subheader("📊 Feature Importances")
    try:
        imp_df = pd.DataFrame(result["importances"].items(), columns=["Feature","Importance"])
        imp_df = imp_df.sort_values("Importance", ascending=True)
        import plotly.express as px
        fig_i = px.bar(imp_df, x="Importance", y="Feature", orientation="h",
            title="Random Forest Feature Importance",
            template="plotly_dark", height=350,
            color="Importance", color_continuous_scale="plasma")
        st.plotly_chart(fig_i, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ {e}")

    # Technical indicators table
    st.subheader("📊 Latest Technical Indicators")
    try:
        last = result["df"].iloc[-1]
        tech = {
            "RSI (14)":     round(safe_float(last.get("rsi")), 2),
            "MACD Hist":    round(safe_float(last.get("macd_hist")), 4),
            "BB Position":  round(safe_float(last.get("bb_pos")), 3),
            "1-Day Return": f"{round(safe_float(last.get('ret1'))*100, 2)}%",
            "5-Day Return": f"{round(safe_float(last.get('ret5'))*100, 2)}%",
            "Volatility":   f"{round(safe_float(last.get('vol10'))*100, 2)}%",
        }
        st.dataframe(pd.DataFrame([tech]), use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"⚠️ {e}")
