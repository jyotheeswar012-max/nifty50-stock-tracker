import streamlit as st
from utils.supabase_auth import require_login

st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")
user = require_login()

import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
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

st.title("🤖 ML Price Direction Predictions")
st.caption(f"Signed in as **{user['full_name']}**")
st.markdown('<span style="background:#ffd600;color:black;padding:2px 10px;border-radius:20px;font-size:13px;font-weight:bold;">EXPERIMENTAL</span> &nbsp; Random Forest — educational use only', unsafe_allow_html=True)
st.markdown("---")

sel = st.selectbox("Select Stock", NIFTY50_NAMES)
sym = NAME_TO_SYM[sel]
period = st.selectbox("Training Period", ["6mo","1y","2y"], index=1)

if st.button("🤖 Run Prediction", type="primary"):
    with st.spinner("Fetching data & training model..."):
        try:
            h = yf.Ticker(sym).history(period=period, auto_adjust=True)
            if h is None or len(h) < 60:
                st.error("❌ Not enough data. Try a longer period.")
                st.stop()

            h = h.copy()
            h["Return"]   = h["Close"].pct_change()
            h["MA5"]      = h["Close"].rolling(5).mean()
            h["MA20"]     = h["Close"].rolling(20).mean()
            h["Vol5"]     = h["Return"].rolling(5).std()
            h["RSI"]      = 100 - (100 / (1 + h["Return"].clip(lower=0).rolling(14).mean() /
                                           (-h["Return"].clip(upper=0).rolling(14).mean()).replace(0, 1e-9)))
            h["Target"]   = (h["Close"].shift(-1) > h["Close"]).astype(int)
            h = h.dropna()

            feats = ["Return","MA5","MA20","Vol5","RSI","Volume"]
            X = h[feats].values
            y = h["Target"].values

            split = int(len(X) * 0.8)
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            sc = StandardScaler()
            X_train = sc.fit_transform(X_train)
            X_test  = sc.transform(X_test)

            clf = RandomForestClassifier(n_estimators=100, random_state=42)
            clf.fit(X_train, y_train)
            acc = clf.score(X_test, y_test)

            last_feat = sc.transform([h[feats].iloc[-1].values])
            pred = clf.predict(last_feat)[0]
            prob = clf.predict_proba(last_feat)[0][pred]

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Model Accuracy", f"{acc*100:.1f}%")
            c2.metric("Tomorrow's Direction", "🟢 UP" if pred == 1 else "🔴 DOWN")
            c3.metric("Confidence", f"{prob*100:.1f}%")

            st.markdown("---")
            fi = pd.DataFrame({"Feature": feats, "Importance": clf.feature_importances_})\
                   .sort_values("Importance", ascending=False)
            st.subheader("📊 Feature Importance")
            st.bar_chart(fi.set_index("Feature"))

            st.info("⚠️ This is a Random Forest classifier trained on technical indicators. "
                    "It is for educational purposes only and NOT financial advice.")
        except Exception as e:
            st.error(f"❌ Error: {e}")
