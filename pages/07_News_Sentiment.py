import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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

# ── Shared chart theme ────────────────────────────────────────────────────────
PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a"),
    margin=dict(l=16, r=16, t=48, b=16),
)
_AXIS = dict(
    tickfont=dict(color="#1e293b", size=11),
    title_font=dict(color="#0f172a", size=12),
    linecolor="#cbd5e1", gridcolor="#f1f5f9", zerolinecolor="#cbd5e1",
)

NSE_STOCKS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "HCLTECH",
    "AXISBANK", "SBIN", "BAJFINANCE", "WIPRO", "SUNPHARMA",
    "TITAN", "TATAMOTORS", "TATASTEEL", "MARUTI", "NTPC",
]

STOCK_SECTORS = {
    "RELIANCE": "Energy", "HDFCBANK": "Financials", "ICICIBANK": "Financials",
    "INFY": "IT", "TCS": "IT", "BHARTIARTL": "Telecom", "ITC": "FMCG",
    "KOTAKBANK": "Financials", "LT": "Industrials", "HCLTECH": "IT",
    "AXISBANK": "Financials", "SBIN": "Financials", "BAJFINANCE": "Financials",
    "WIPRO": "IT", "SUNPHARMA": "Pharma", "TITAN": "Consumer",
    "TATAMOTORS": "Automobile", "TATASTEEL": "Metals", "MARUTI": "Automobile",
    "NTPC": "Power",
}

np.random.seed(int(datetime.now().strftime("%H%M")) // 10)
base_scores = {
    "RELIANCE": 0.62, "HDFCBANK": 0.55, "ICICIBANK": 0.58, "INFY": 0.45, "TCS": 0.50,
    "BHARTIARTL": 0.70, "ITC": 0.40, "KOTAKBANK": 0.52, "LT": 0.65, "HCLTECH": 0.48,
    "AXISBANK": 0.35, "SBIN": 0.30, "BAJFINANCE": 0.60, "WIPRO": 0.42, "SUNPHARMA": 0.55,
    "TITAN": 0.68, "TATAMOTORS": 0.38, "TATASTEEL": 0.28, "MARUTI": 0.50, "NTPC": 0.45,
}

np.random.seed(42)
DAYS = ["Day -6", "Day -5", "Day -4", "Day -3", "Day -2", "Yesterday", "Today"]

SAMPLE_HEADLINES = {
    "RELIANCE": [
        ("Reliance Jio crosses 500 million subscribers milestone", "positive"),
        ("RIL Q4 profit beats estimates on strong telecom growth", "positive"),
        ("Reliance Retail eyes global expansion into Southeast Asia", "positive"),
    ],
    "HDFCBANK": [
        ("HDFC Bank net interest margin improves to 4.2% in Q4", "positive"),
        ("HDFC Bank to raise Rs.50,000 crore via bonds this year", "neutral"),
        ("RBI approves HDFC Bank's new branch expansion plan", "positive"),
    ],
    "ICICIBANK": [
        ("ICICI Bank Q4 net profit rises 18% YoY to Rs.11,672 crore", "positive"),
        ("ICICI Bank retail loan book grows 22% on strong demand", "positive"),
        ("ICICI Bank launches AI-powered credit scoring platform", "positive"),
    ],
    "INFY": [
        ("Infosys revises FY27 revenue guidance upward to 6-8%", "positive"),
        ("Infosys wins $1.5B deal with European banking consortium", "positive"),
        ("Infosys faces headwinds from US visa restrictions", "negative"),
    ],
    "TCS": [
        ("TCS Q4 PAT grows 5% YoY, beats Street estimates", "positive"),
        ("TCS announces Rs.17,000 crore share buyback programme", "positive"),
        ("TCS hiring to slow amid global IT spending caution", "negative"),
    ],
    "BHARTIARTL": [
        ("Airtel posts record EBITDA margin of 52% in Q4 FY26", "positive"),
        ("Bharti Airtel 5G rollout reaches 700 cities nationwide", "positive"),
        ("Airtel Africa subscriber base grows 8% QoQ", "positive"),
    ],
    "ITC": [
        ("ITC Hotels demerger receives NCLT approval, listing expected Q3", "positive"),
        ("ITC cigarette volumes flat as rural demand stays muted", "neutral"),
        ("ITC FMCG business crosses Rs.20,000 crore revenue milestone", "positive"),
    ],
    "KOTAKBANK": [
        ("Kotak Mahindra Bank Q4 PAT up 26% at Rs.7,250 crore", "positive"),
        ("RBI lifts digital onboarding restrictions on Kotak Bank", "positive"),
        ("Kotak MD Uday Kotak steps down; transition plan in place", "neutral"),
    ],
    "LT": [
        ("L&T secures Rs.15,000 crore infrastructure order from NHAI", "positive"),
        ("Larsen & Toubro Q4 order inflows rise 28% YoY", "positive"),
        ("L&T Technology Services margin pressured by wage hikes", "negative"),
    ],
    "HCLTECH": [
        ("HCL Tech Q4 revenue growth beats guidance at 6.7%", "positive"),
        ("HCL Technologies wins digital transformation deal with UK retailer", "positive"),
        ("HCL Tech attrition falls to 12.1%, lowest in 8 quarters", "positive"),
    ],
    "AXISBANK": [
        ("Axis Bank net NPA falls to 0.36%, best-ever quarterly figure", "positive"),
        ("Axis Bank credit card market share slips amid Citi integration", "negative"),
        ("Axis Bank raises Rs.12,000 crore via QIP for growth capital", "neutral"),
    ],
    "SBIN": [
        ("SBI reports record quarterly profit of Rs.18,000 crore", "positive"),
        ("SBI NPAs inch up amid rural credit stress in Q4", "negative"),
        ("SBI Home Loans sees 20% growth in festive season", "positive"),
    ],
    "BAJFINANCE": [
        ("Bajaj Finance AUM crosses Rs.4 lakh crore, up 27% YoY", "positive"),
        ("Bajaj Finance Q4 net interest income beats estimates", "positive"),
        ("RBI scrutiny on NBFC lending practices adds uncertainty", "negative"),
    ],
    "WIPRO": [
        ("Wipro Q4 IT services revenue grows 1.2% QoQ in constant currency", "neutral"),
        ("Wipro wins $600M deal in North America banking segment", "positive"),
        ("Wipro CEO signals cautious FY27 outlook amid macro uncertainty", "negative"),
    ],
    "SUNPHARMA": [
        ("Sun Pharma specialty business revenue surges 35% in US market", "positive"),
        ("Sun Pharmaceutical Q4 PAT up 22%, dividend declared", "positive"),
        ("Sun Pharma faces FDA inspection at Halol plant", "negative"),
    ],
    "TITAN": [
        ("Titan Q4 jewellery sales up 24% driven by wedding season", "positive"),
        ("Titan Company opens 200 new Tanishq stores in FY26", "positive"),
        ("Titan watches segment sees margin pressure from gold prices", "neutral"),
    ],
    "TATAMOTORS": [
        ("Tata Motors JLR faces chip shortage delays in EU markets", "negative"),
        ("Tata EV sales surge 45% YoY in domestic market", "positive"),
        ("Tata Motors revises FY27 guidance cautiously lower", "negative"),
    ],
    "TATASTEEL": [
        ("Tata Steel UK turnaround plan approved; 2,800 jobs saved", "positive"),
        ("Tata Steel Q4 earnings hit by weak European steel demand", "negative"),
        ("Indian steel capacity expansion on track at Kalinganagar", "positive"),
    ],
    "MARUTI": [
        ("Maruti Suzuki FY26 sales cross 2.1 million units, all-time high", "positive"),
        ("Maruti hybrid models gain share as EV adoption stays slow", "positive"),
        ("Maruti Q4 margins pressured by rising commodity costs", "negative"),
    ],
    "NTPC": [
        ("NTPC Green Energy IPO oversubscribed 2.5x on robust demand", "positive"),
        ("NTPC adds 3,200 MW renewable capacity in FY26", "positive"),
        ("NTPC coal supply disruptions affect Q4 plant load factor", "negative"),
    ],
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

sentiments = {
    sym: round(max(0.0, min(1.0, base_scores.get(sym, 0.5) + np.random.uniform(-0.05, 0.05))), 3)
    for sym in NSE_STOCKS
}
avg_score = np.mean(list(sentiments.values()))
bullish = sum(1 for s in sentiments.values() if s >= 0.55)
bearish = sum(1 for s in sentiments.values() if s <= 0.40)
neutral_count = len(sentiments) - bullish - bearish

m1, m2, m3, m4 = st.columns(4)
m1.metric("Avg Sentiment", f"{avg_score:.2f} / 1.0")
m2.metric("🟢 Bullish", bullish)
m3.metric("🔴 Bearish", bearish)
m4.metric("🟡 Neutral", neutral_count)

if avg_score >= 0.6:
    st.success("📈 **Market mood: BULLISH**")
elif avg_score <= 0.4:
    st.error("📉 **Market mood: BEARISH**")
else:
    st.warning("📊 **Market mood: NEUTRAL**")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ── Stock Sentiment Bar Chart ─────────────────────────────────────────────────
df_sent = pd.DataFrame([
    {
        "Symbol": sym,
        "Sentiment Score": score,
        "Sector": STOCK_SECTORS.get(sym, "Other"),
        "Signal": "🟢 Bullish" if score >= 0.55 else ("🔴 Bearish" if score <= 0.40 else "🟡 Neutral"),
    }
    for sym, score in sentiments.items()
]).sort_values("Sentiment Score", ascending=False)

try:
    fig = px.bar(
        df_sent, x="Symbol", y="Sentiment Score", color="Sentiment Score",
        color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
        color_continuous_midpoint=0.5,
        text="Sentiment Score", title="Stock Sentiment Scores (All 20 Stocks)", height=380,
    )
    fig.update_traces(
        texttemplate="%{text:.2f}", textposition="outside",
        textfont=dict(color="#1e293b", size=11),
    )
    fig.add_hline(y=0.5, line_dash="dot", line_color="#94a3b8",
                  annotation_text="Neutral",
                  annotation_font=dict(color="#475569", size=11))
    fig.update_layout(
        **PLT_LAYOUT,
        coloraxis_showscale=False,
        xaxis=dict(**_AXIS, title="Symbol"),
        yaxis=dict(**_AXIS, title="Sentiment Score", range=[0, 1.12]),
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.dataframe(df_sent, use_container_width=True, hide_index=True)

# ── Sector Sentiment Chart ────────────────────────────────────────────────────
st.markdown("<p class='sec-label'>Sector-wise Average Sentiment</p>", unsafe_allow_html=True)
try:
    df_sector = (
        df_sent.groupby("Sector")["Sentiment Score"]
        .mean()
        .reset_index()
        .rename(columns={"Sentiment Score": "Avg Sentiment"})
        .sort_values("Avg Sentiment", ascending=True)
    )
    fig_sec = px.bar(
        df_sector, x="Avg Sentiment", y="Sector",
        orientation="h",
        color="Avg Sentiment",
        color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
        color_continuous_midpoint=0.5,
        text="Avg Sentiment",
        title="Average Sentiment Score by Sector",
        height=340,
    )
    fig_sec.update_traces(
        texttemplate="%{text:.2f}", textposition="outside",
        textfont=dict(color="#1e293b", size=11),
    )
    fig_sec.add_vline(x=0.5, line_dash="dot", line_color="#94a3b8",
                      annotation_text="Neutral",
                      annotation_font=dict(color="#475569", size=11))
    fig_sec.update_layout(
        **PLT_LAYOUT,
        coloraxis_showscale=False,
        xaxis=dict(**_AXIS, title="Avg Sentiment", range=[0, 0.92]),
        yaxis=dict(**_AXIS, title="Sector"),
    )
    st.plotly_chart(fig_sec, use_container_width=True)
except Exception as e:
    st.warning(f"Sector chart error: {e}")

# ── 7-Day Sentiment Trend Chart ───────────────────────────────────────────────
st.markdown("<p class='sec-label'>7-Day Market Sentiment Trend</p>", unsafe_allow_html=True)
try:
    np.random.seed(7)
    trend_data = []
    for day in DAYS:
        for sym in NSE_STOCKS:
            base = base_scores.get(sym, 0.5)
            score = round(max(0.0, min(1.0, base + np.random.uniform(-0.12, 0.12))), 3)
            trend_data.append({"Day": day, "Symbol": sym, "Score": score})
    df_trend = pd.DataFrame(trend_data)
    df_avg_trend = df_trend.groupby("Day")["Score"].mean().reset_index()
    df_avg_trend["Day"] = pd.Categorical(df_avg_trend["Day"], categories=DAYS, ordered=True)
    df_avg_trend = df_avg_trend.sort_values("Day")

    top5 = df_sent["Symbol"].head(5).tolist()
    df_top5_trend = df_trend[df_trend["Symbol"].isin(top5)].copy()
    df_top5_trend["Day"] = pd.Categorical(df_top5_trend["Day"], categories=DAYS, ordered=True)
    df_top5_trend = df_top5_trend.sort_values("Day")

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=df_avg_trend["Day"], y=df_avg_trend["Score"],
        mode="lines+markers",
        name="Market Avg",
        line=dict(color="#6366f1", width=3),
        marker=dict(size=8, color="#6366f1"),
    ))
    colors = ["#10b981", "#f59e0b", "#ef4444", "#0ea5e9", "#a855f7"]
    for i, sym in enumerate(top5):
        d = df_top5_trend[df_top5_trend["Symbol"] == sym]
        fig_trend.add_trace(go.Scatter(
            x=d["Day"], y=d["Score"],
            mode="lines+markers",
            name=sym,
            line=dict(color=colors[i], width=1.5, dash="dot"),
            marker=dict(size=5, color=colors[i]),
        ))
    fig_trend.add_hline(
        y=0.5, line_dash="dash", line_color="#94a3b8",
        annotation_text="Neutral 0.5",
        annotation_font=dict(color="#475569", size=11),
    )
    fig_trend.update_layout(
        **PLT_LAYOUT, height=360,
        title="7-Day Sentiment Trend — Market Avg & Top 5 Bullish Stocks",
        xaxis=dict(**_AXIS, title="Day"),
        yaxis=dict(**_AXIS, title="Sentiment Score", range=[0.1, 0.9]),
        legend=dict(
            font=dict(size=11, color="#1e293b"),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#e2e8f0", borderwidth=1,
        ),
    )
    st.plotly_chart(fig_trend, use_container_width=True)
except Exception as e:
    st.warning(f"Trend chart error: {e}")

# ── Individual Stock Headlines ─────────────────────────────────────────────────
st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
st.markdown("<p class='sec-label'>Stock Headlines</p>", unsafe_allow_html=True)
sel_stock = st.selectbox("Select Stock", NSE_STOCKS, key="ns_stock")
headlines = SAMPLE_HEADLINES.get(sel_stock, [])
if headlines:
    for headline, tone in headlines:
        if tone == "positive":
            st.success(f"🟢 {headline}")
        elif tone == "negative":
            st.error(f"🔴 {headline}")
        else:
            st.info(f"🟡 {headline}")
else:
    st.info("No headlines available for this stock.")

# ── Full Sentiment Table ───────────────────────────────────────────────────────
st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
st.dataframe(df_sent[["Symbol", "Sector", "Sentiment Score", "Signal"]], use_container_width=True, hide_index=True)
st.caption("⚠️ Sentiment scores are simulated for educational purposes. Not financial advice.")
