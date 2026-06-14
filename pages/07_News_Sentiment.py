import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="News Sentiment", page_icon="📰", layout="wide")

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

PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a"),
    margin=dict(l=16, r=16, t=48, b=16),
)

NSE_STOCKS = ["RELIANCE","HDFCBANK","ICICIBANK","INFY","TCS","BHARTIARTL","ITC","KOTAKBANK","LT","HCLTECH","AXISBANK","SBIN","BAJFINANCE","WIPRO","SUNPHARMA","TITAN","TATAMOTORS","TATASTEEL","MARUTI","NTPC"]

np.random.seed(int(datetime.now().strftime("%H%M")) // 10)
base_scores = {"RELIANCE":0.62,"HDFCBANK":0.55,"ICICIBANK":0.58,"INFY":0.45,"TCS":0.50,"BHARTIARTL":0.70,"ITC":0.40,"KOTAKBANK":0.52,"LT":0.65,"HCLTECH":0.48,"AXISBANK":0.35,"SBIN":0.30,"BAJFINANCE":0.60,"WIPRO":0.42,"SUNPHARMA":0.55,"TITAN":0.68,"TATAMOTORS":0.38,"TATASTEEL":0.28,"MARUTI":0.50,"NTPC":0.45}

SAMPLE_HEADLINES = {
    "RELIANCE":[("Reliance Jio crosses 500 million subscribers milestone","positive"),("RIL Q4 profit beats estimates on strong telecom growth","positive"),("Reliance Retail eyes global expansion","positive")],
    "HDFCBANK":[("HDFC Bank net interest margin improves to 4.2%","positive"),("HDFC Bank to raise ₹50,000 crore via bonds","neutral"),("RBI approves HDFC Bank's new branch expansion","positive")],
    "INFY":[("Infosys revises FY27 revenue guidance upward to 6-8%","positive"),("Infosys wins $1.5B deal with European banking consortium","positive"),("Infosys faces headwinds from US visa restrictions","negative")],
    "TCS":[("TCS Q4 PAT grows 5% YoY, beats Street estimates","positive"),("TCS announces ₹17,000 crore share buyback","positive"),("TCS hiring to slow amid global IT spending caution","negative")],
    "SBIN":[("SBI reports record quarterly profit of ₹18,000 crore","positive"),("SBI NPAs inch up amid rural credit stress","negative"),("SBI Home Loans sees 20% growth in festive season","positive")],
    "TATAMOTORS":[("Tata Motors JLR faces chip shortage delays in EU","negative"),("Tata EV sales surge 45% YoY in domestic market","positive"),("Tata Motors revises FY27 guidance cautiously lower","negative")],
}

st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">📰</div>
  <div>
    <div class="hero-title">News Sentiment</div>
    <div class="hero-sub"><span class="ui-badge badge-live">LIVE</span>&nbsp; Sentiment scores for NSE stocks</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<p class='sec-label'>Overall Market Sentiment</p>", unsafe_allow_html=True)

sentiments = {sym: round(max(0.0, min(1.0, base_scores.get(sym, 0.5) + np.random.uniform(-0.05, 0.05))), 3) for sym in NSE_STOCKS}
avg_score = np.mean(list(sentiments.values()))
bullish = sum(1 for s in sentiments.values() if s >= 0.55)
bearish = sum(1 for s in sentiments.values() if s <= 0.40)
neutral_count = len(sentiments) - bullish - bearish

m1, m2, m3, m4 = st.columns(4)
m1.metric("Avg Sentiment", f"{avg_score:.2f} / 1.0")
m2.metric("🟢 Bullish", bullish)
m3.metric("🔴 Bearish", bearish)
m4.metric("🟡 Neutral", neutral_count)

if avg_score >= 0.6: st.success("📈 **Market mood: BULLISH**")
elif avg_score <= 0.4: st.error("📉 **Market mood: BEARISH**")
else: st.warning("📊 **Market mood: NEUTRAL**")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

df_sent = pd.DataFrame([{"Symbol": sym, "Sentiment Score": score, "Signal": "🟢 Bullish" if score >= 0.55 else ("🔴 Bearish" if score <= 0.40 else "🟡 Neutral")} for sym, score in sentiments.items()]).sort_values("Sentiment Score", ascending=False)

try:
    fig = px.bar(df_sent, x="Symbol", y="Sentiment Score", color="Sentiment Score",
        color_continuous_scale=["#ef4444","#f59e0b","#10b981"], color_continuous_midpoint=0.5,
        text="Sentiment Score", title="Stock Sentiment Scores", height=360)
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.add_hline(y=0.5, line_dash="dot", line_color="#94a3b8", annotation_text="Neutral")
    fig.update_layout(**PLT_LAYOUT, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.dataframe(df_sent, use_container_width=True, hide_index=True)

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
st.markdown("<p class='sec-label'>Stock Headlines</p>", unsafe_allow_html=True)
sel_stock = st.selectbox("Select Stock", list(SAMPLE_HEADLINES.keys()), key="ns_stock")
for headline, tone in SAMPLE_HEADLINES.get(sel_stock, []):
    if tone == "positive": st.success(f"🟢 {headline}")
    elif tone == "negative": st.error(f"🔴 {headline}")
    else: st.info(f"🟡 {headline}")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
st.dataframe(df_sent, use_container_width=True, hide_index=True)
st.caption("⚠️ Sentiment scores are simulated for educational purposes. Not financial advice.")
