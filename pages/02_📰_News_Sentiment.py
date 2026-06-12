"""
Page: News & Sentiment Analysis
Fetches headlines via NewsAPI (free tier) or falls back to Yahoo Finance
news. Runs VADER (rule-based) sentiment scoring — no heavy ML deps.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="News & Sentiment", page_icon="📰", layout="wide")

NIFTY50_NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro",
    "HCL Technologies","Axis Bank","State Bank of India","Bajaj Finance",
    "Wipro","Asian Paints","Maruti Suzuki","Sun Pharmaceutical",
    "Titan Company","UltraTech Cement","ONGC","NTPC","Power Grid Corp",
    "Mahindra & Mahindra","Tata Motors","Tata Steel","JSW Steel",
    "Hindalco Industries","Adani Enterprises","Adani Ports","Bajaj Finserv",
    "Bajaj Auto","Hero MotoCorp","Cipla","Dr. Reddy's Labs",
    "Divi's Laboratories","Eicher Motors","Grasim Industries",
    "HDFC Life Insurance","SBI Life Insurance","IndusInd Bank",
    "Tata Consumer Products","Britannia Industries","Nestle India",
    "Hindustan Unilever","Coal India","BPCL","Tech Mahindra",
    "L&T Finance","Shriram Finance","Bharat Electronics",
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

# ---- Lightweight VADER-style scorer (no extra deps) ----
POS_WORDS = {
    "surge","jump","gain","rally","rise","beat","profit","growth","record",
    "strong","positive","upgrade","buy","bull","outperform","high","success",
    "revenue","expand","robust","excellent","soar","peak","boom","wins",
}
NEG_WORDS = {
    "fall","drop","loss","crash","decline","miss","weak","negative","sell",
    "bear","downgrade","underperform","low","fail","debt","warning","risk",
    "concern","disappoint","plunge","tumble","slump","cut","penalty",
}

def score_text(text: str) -> float:
    if not text:
        return 0.0
    words = re.findall(r"\b\w+\b", text.lower())
    pos = sum(1 for w in words if w in POS_WORDS)
    neg = sum(1 for w in words if w in NEG_WORDS)
    total = pos + neg
    return round((pos - neg) / total, 3) if total > 0 else 0.0

def sentiment_label(score):
    if score > 0.1:  return "🟢 Positive"
    elif score < -0.1: return "🔴 Negative"
    else:              return "🟡 Neutral"

@st.cache_data(ttl=600)
def get_yahoo_news(sym: str) -> list:
    """Fetch news from Yahoo Finance via yfinance."""
    try:
        tk   = yf.Ticker(sym)
        news = tk.news or []
        rows = []
        for n in news[:15]:
            ct  = n.get("content", {})
            title = ct.get("title", "") if isinstance(ct, dict) else str(n.get("title", ""))
            summ  = ct.get("summary", "") if isinstance(ct, dict) else ""
            pub   = ct.get("pubDate",  "") if isinstance(ct, dict) else ""
            link  = ""
            if isinstance(ct, dict):
                cp = ct.get("canonicalUrl", {})
                link = cp.get("url", "") if isinstance(cp, dict) else ""
            text  = f"{title} {summ}"
            score = score_text(text)
            rows.append({
                "Title":     title[:120],
                "Published": pub[:16] if pub else "N/A",
                "Sentiment": sentiment_label(score),
                "Score":     score,
                "Link":      link,
            })
        return rows
    except Exception:
        return []

# ---- UI ----
st.title("📰 News & Sentiment Analysis")
st.markdown("""
Fetches the latest headlines for any Nifty 50 stock from **Yahoo Finance**
and scores them with a rule-based sentiment engine.
> Scores range from **-1.0** (very negative) to **+1.0** (very positive).
""")

col1, col2 = st.columns([3, 1])
with col1:
    sel_name = st.selectbox("🏢 Select Company", NIFTY50_NAMES)
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh = st.button("🔄 Refresh News")

sym = NAME_TO_SYM[sel_name]

if refresh:
    st.cache_data.clear()

with st.spinner(f"Fetching news for {sel_name}..."):
    news_rows = get_yahoo_news(sym)

if not news_rows:
    st.warning("⚠️ No news found. Yahoo Finance may be rate-limiting. Try again in a minute.")
else:
    df = pd.DataFrame(news_rows)

    # Summary metrics
    pos = (df["Score"] > 0.1).sum()
    neg = (df["Score"] < -0.1).sum()
    neu = len(df) - pos - neg
    avg = round(df["Score"].mean(), 3)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📰 Headlines", len(df))
    c2.metric("🟢 Positive",  pos)
    c3.metric("🔴 Negative",  neg)
    c4.metric("📊 Avg Score",  avg,
        delta="Bullish" if avg > 0.1 else ("Bearish" if avg < -0.1 else "Neutral"))

    # Sentiment gauge bar
    try:
        import plotly.graph_objects as go
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=avg,
            delta={"reference": 0},
            gauge={
                "axis": {"range": [-1, 1]},
                "bar":  {"color": "#00c853" if avg > 0 else "#ff1744"},
                "steps": [
                    {"range": [-1, -0.1], "color": "#ff1744"},
                    {"range": [-0.1, 0.1], "color": "#ffd600"},
                    {"range": [0.1,  1],   "color": "#00c853"},
                ],
                "threshold": {"line": {"color": "white", "width": 3}, "value": avg},
            },
            title={"text": f"{sel_name} — Sentiment Score"},
        ))
        fig_g.update_layout(template="plotly_dark", height=280)
        st.plotly_chart(fig_g, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ {e}")

    st.markdown("---")
    st.subheader("📰 Headlines")
    for _, row in df.iterrows():
        color = "🟢" if row["Score"] > 0.1 else ("🔴" if row["Score"] < -0.1 else "🟡")
        link  = f" &nbsp; [Read ↗]({row['Link']})" if row["Link"] else ""
        st.markdown(
            f"{color} **{row['Title']}**{link}  "
            f"<span style='color:#9e9e9e;font-size:12px'>{row['Published']} &nbsp; Score: `{row['Score']}`</span>",
            unsafe_allow_html=True,
        )
    st.markdown("---")

    # Score time-series bar
    try:
        import plotly.express as px
        df_plot = df.copy()
        df_plot["color"] = df_plot["Score"].apply(
            lambda x: "Positive" if x > 0.1 else ("Negative" if x < -0.1 else "Neutral"))
        fig_b = px.bar(df_plot.reset_index(), x="index", y="Score",
            color="color",
            color_discrete_map={"Positive":"#00c853","Negative":"#ff1744","Neutral":"#ffd600"},
            title=f"{sel_name} — Headline Sentiment Scores",
            template="plotly_dark", height=300,
            labels={"index":"Article #"})
        st.plotly_chart(fig_b, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ {e}")
