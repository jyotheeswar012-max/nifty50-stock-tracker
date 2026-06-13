"""
Page: News & AI Sentiment Scores
"""
import streamlit as st
from utils.supabase_auth import require_login

st.set_page_config(page_title="News Sentiment", page_icon="📰", layout="wide")
user = require_login()

import pandas as pd
import plotly.express as px
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

def sentiment_score(text: str) -> tuple[str, float, str]:
    """Return (label, score, emoji) using TextBlob polarity."""
    try:
        from textblob import TextBlob
        pol = TextBlob(text).sentiment.polarity
        if pol > 0.1:    return "Positive", round(pol, 3), "🟢"
        elif pol < -0.1: return "Negative", round(abs(pol), 3), "🔴"
        else:            return "Neutral",  round(abs(pol), 3), "🟽"
    except ImportError:
        return "N/A", 0.0, "❓"

st.title("📰 News & AI Sentiment")
st.caption(f"Signed in as **{user['full_name']}** • Powered by NewsAPI + TextBlob")

selected = st.selectbox("Select Stock", NIFTY50_NAMES)

try:
    from newsapi import NewsApiClient
    api_key = st.secrets.get("newsapi", {}).get("key", "")
    if not api_key:
        raise ValueError("No NewsAPI key")
    newsapi = NewsApiClient(api_key=api_key)

    if st.button("🔍 Fetch News + Analyse Sentiment", type="primary"):
        with st.spinner("Fetching & analysing..."):
            res = newsapi.get_everything(
                q=selected, language="en", sort_by="publishedAt", page_size=15
            )
        articles = res.get("articles", [])
        if not articles:
            st.info("No recent news found.")
        else:
            scored = []
            for a in articles:
                text = f"{a.get('title','')} {a.get('description','')}"
                label, score, emoji = sentiment_score(text)
                scored.append({
                    "title":  a["title"],
                    "url":    a["url"],
                    "source": a.get("source", {}).get("name", ""),
                    "date":   a.get("publishedAt", "")[:10],
                    "sentiment": label,
                    "score":     score,
                    "emoji":     emoji,
                    "desc":      a.get("description", ""),
                })

            # ── Summary pie chart ────────────────────────────────────
            counts = pd.Series([s["sentiment"] for s in scored]).value_counts().reset_index()
            counts.columns = ["Sentiment", "Count"]
            colours = {"Positive": "#00c853", "Neutral": "#ffd600", "Negative": "#ff1744"}
            fig_pie = px.pie(
                counts, names="Sentiment", values="Count",
                color="Sentiment", color_discrete_map=colours,
                title=f"Sentiment Summary — {selected} ({len(scored)} articles)",
                hole=0.45,
            )
            fig_pie.update_layout(template="plotly_dark", height=320)
            st.plotly_chart(fig_pie, use_container_width=True)

            # ── Overall verdict ──────────────────────────────────────
            pos = sum(1 for s in scored if s["sentiment"] == "Positive")
            neg = sum(1 for s in scored if s["sentiment"] == "Negative")
            if pos > neg:
                st.success(f"🟢 Overall sentiment is **POSITIVE** ({pos}/{len(scored)} articles)")
            elif neg > pos:
                st.error(f"🔴 Overall sentiment is **NEGATIVE** ({neg}/{len(scored)} articles)")
            else:
                st.info(f"🟽 Overall sentiment is **NEUTRAL")

            st.markdown("---")

            # ── Article cards ────────────────────────────────────────
            for a in scored:
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"**[{a['title']}]({a['url']})**")
                        st.caption(f"{a['source']} • {a['date']}")
                        if a["desc"]: st.write(a["desc"])
                    with c2:
                        st.markdown(f"## {a['emoji']}")
                        st.caption(f"{a['sentiment']}\n{a['score']:.2f}")

except Exception as e:
    st.info("💡 Add a **NewsAPI key** in Streamlit Secrets under `[newsapi] key = 'your_key'` to enable this page.")
    st.caption(f"Get a free key at [newsapi.org](https://newsapi.org) • Error: {e}")
    st.markdown("---")
    st.subheader("🧪 TextBlob Sentiment Demo (no API key needed)")
    demo_text = st.text_area("Paste any financial headline:",
        value="Infosys reports strong quarterly earnings, beats analyst estimates.")
    if demo_text:
        label, score, emoji = sentiment_score(demo_text)
        st.markdown(f"### {emoji} {label} (score: {score:.3f})")
