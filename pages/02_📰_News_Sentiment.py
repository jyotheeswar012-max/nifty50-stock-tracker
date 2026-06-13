"""
Page: News Sentiment Analyser  —  light theme
"""
import streamlit as st
from utils.theme import inject

st.set_page_config(page_title="News Sentiment", page_icon="📰", layout="wide")
inject()

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

try:
    from textblob import TextBlob
    TEXTBLOB_OK = True
except ImportError:
    TEXTBLOB_OK = False

NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro","HCL Technologies",
    "Axis Bank","State Bank of India","Bajaj Finance","Wipro","Asian Paints",
    "Maruti Suzuki","Sun Pharmaceutical","Titan Company","UltraTech Cement","ONGC",
]
SYMS = [
    "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS",
    "BHARTIARTL.NS","ITC.NS","KOTAKBANK.NS","LT.NS","HCLTECH.NS",
    "AXISBANK.NS","SBIN.NS","BAJFINANCE.NS","WIPRO.NS","ASIANPAINT.NS",
    "MARUTI.NS","SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS","ONGC.NS",
]
N2S = dict(zip(NAMES, SYMS))

# ── Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.5rem;">
  <div style="width:52px;height:52px;border-radius:50%;
              background:linear-gradient(135deg,#06b6d4,#3b82f6);
              display:flex;align-items:center;justify-content:center;
              font-size:1.5rem;color:#fff;box-shadow:0 4px 14px rgba(6,182,212,.35);">
    📰
  </div>
  <div>
    <div class="ui-page-title" style="font-size:1.7rem;">News Sentiment</div>
    <div class="ui-caption" style="margin:0;">Analyse market mood from recent headlines</div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("<span class='ui-badge badge-live'>LIVE</span>&nbsp; TextBlob NLP sentiment analysis", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

if not TEXTBLOB_OK:
    st.error("❌ `textblob` not installed. Add it to requirements.txt and redeploy."); st.stop()

st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
stock = st.selectbox("🏛️ Select Company", NAMES, key="news_stock")
period = st.selectbox("📅 History period", ["1mo","3mo","6mo"], index=0, key="news_period")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def fetch_news_prices(sym, period):
    try:
        t = yf.Ticker(sym)
        h = t.history(period=period, auto_adjust=True)
        n = t.news or []
        return h, n
    except Exception:
        return pd.DataFrame(), []

with st.spinner("🔍 Fetching data…"):
    hist, news = fetch_news_prices(N2S[stock], period)

if hist.empty:
    st.warning("⚠️ Could not fetch price data.")
else:
    cp = float(hist["Close"].iloc[-1])
    pp = float(hist["Close"].iloc[-2]) if len(hist)>1 else cp
    ch = cp-pp; pt=(ch/pp*100) if pp else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Current Price", f"₹{cp:,.2f}")
    c2.metric("Change", f"{ch:+.2f}")
    c3.metric("% Change", f"{pt:+.2f}%")
    c4.metric("Period High", f"₹{hist['High'].max():,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown(f"#### 📈 {stock} — Price History")
    try:
        fig = px.area(hist.reset_index(), x="Date", y="Close",
            title=f"{stock} Close Price",
            template="plotly_white",
            color_discrete_sequence=["#6366f1"],
            height=320)
        fig.update_traces(line_color="#6366f1", fillcolor="rgba(99,102,241,0.1)")
        fig.update_layout(paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
                          font_color="#1a1a2e", margin=dict(t=40,b=20))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ {e}")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Sentiment ────────────────────────────────────────────────────────────
st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
st.markdown("#### 🧠 Headline Sentiment Analysis")

if not news:
    st.info("💬 No recent news found for this stock via Yahoo Finance API.")
else:
    rows = []
    for item in news[:20]:
        title = item.get("title","")
        if not title: continue
        blob = TextBlob(title)
        pol  = blob.sentiment.polarity
        sub  = blob.sentiment.subjectivity
        label = "🟢 Positive" if pol>0.1 else ("🔴 Negative" if pol<-0.1 else "⚪ Neutral")
        link  = item.get("link","")
        rows.append({"Headline":title, "Sentiment":label,
                     "Polarity":round(pol,3), "Subjectivity":round(sub,3), "Link":link})
    if rows:
        df = pd.DataFrame(rows)
        pos = len(df[df["Sentiment"]=="🟢 Positive"])
        neg = len(df[df["Sentiment"]=="🔴 Negative"])
        neu = len(df[df["Sentiment"]=="⚪ Neutral"])
        m1,m2,m3 = st.columns(3)
        m1.metric("🟢 Positive", pos)
        m2.metric("🔴 Negative", neg)
        m3.metric("⚪ Neutral",  neu)
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            fig_s = px.pie(values=[pos,neg,neu],
                names=["🟢 Positive","🔴 Negative","⚪ Neutral"],
                color_discrete_sequence=["#10b981","#ef4444","#9ca3af"],
                title="Sentiment Distribution",
                template="plotly_white", height=300)
            fig_s.update_layout(paper_bgcolor="#ffffff", font_color="#1a1a2e")
            st.plotly_chart(fig_s, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ {e}")
        st.dataframe(df[["Headline","Sentiment","Polarity","Subjectivity"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("💬 No headlines with text found.")
st.markdown("</div>", unsafe_allow_html=True)
