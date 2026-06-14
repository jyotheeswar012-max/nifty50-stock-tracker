import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="News Sentiment — NSE Tracker",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.theme import inject
inject()

try:
    from utils.supabase_auth import get_current_user, logout, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def logout(): pass
    def is_guest(): return True
    def login_nudge(f=""): st.info("💡 Sign in to save your data.")

try:
    from textblob import TextBlob
    TEXTBLOB_OK = True
except ImportError:
    TEXTBLOB_OK = False

NIFTY50 = [
    {"symbol":"RELIANCE.NS",   "name":"Reliance Industries"},
    {"symbol":"HDFCBANK.NS",   "name":"HDFC Bank"},
    {"symbol":"ICICIBANK.NS",  "name":"ICICI Bank"},
    {"symbol":"INFY.NS",       "name":"Infosys"},
    {"symbol":"TCS.NS",        "name":"TCS"},
    {"symbol":"BHARTIARTL.NS", "name":"Bharti Airtel"},
    {"symbol":"ITC.NS",        "name":"ITC"},
    {"symbol":"KOTAKBANK.NS",  "name":"Kotak Mahindra Bank"},
    {"symbol":"LT.NS",         "name":"Larsen & Toubro"},
    {"symbol":"HCLTECH.NS",    "name":"HCL Technologies"},
    {"symbol":"AXISBANK.NS",   "name":"Axis Bank"},
    {"symbol":"SBIN.NS",       "name":"State Bank of India"},
    {"symbol":"BAJFINANCE.NS", "name":"Bajaj Finance"},
    {"symbol":"WIPRO.NS",      "name":"Wipro"},
    {"symbol":"ASIANPAINT.NS", "name":"Asian Paints"},
    {"symbol":"MARUTI.NS",     "name":"Maruti Suzuki"},
    {"symbol":"SUNPHARMA.NS",  "name":"Sun Pharmaceutical"},
    {"symbol":"TITAN.NS",      "name":"Titan Company"},
    {"symbol":"ULTRACEMCO.NS", "name":"UltraTech Cement"},
    {"symbol":"ONGC.NS",       "name":"ONGC"},
    {"symbol":"NTPC.NS",       "name":"NTPC"},
    {"symbol":"POWERGRID.NS",  "name":"Power Grid Corp"},
    {"symbol":"M&M.NS",        "name":"Mahindra & Mahindra"},
    {"symbol":"TATAMOTORS.NS", "name":"Tata Motors"},
    {"symbol":"TATASTEEL.NS",  "name":"Tata Steel"},
    {"symbol":"JSWSTEEL.NS",   "name":"JSW Steel"},
    {"symbol":"HINDALCO.NS",   "name":"Hindalco Industries"},
    {"symbol":"ADANIENT.NS",   "name":"Adani Enterprises"},
    {"symbol":"ADANIPORTS.NS", "name":"Adani Ports"},
    {"symbol":"BAJAJFINSV.NS", "name":"Bajaj Finserv"},
    {"symbol":"BAJAJAUTO.NS",  "name":"Bajaj Auto"},
    {"symbol":"HEROMOTOCO.NS", "name":"Hero MotoCorp"},
    {"symbol":"CIPLA.NS",      "name":"Cipla"},
    {"symbol":"DRREDDY.NS",    "name":"Dr. Reddy's Labs"},
    {"symbol":"DIVISLAB.NS",   "name":"Divi's Laboratories"},
    {"symbol":"EICHERMOT.NS",  "name":"Eicher Motors"},
    {"symbol":"GRASIM.NS",     "name":"Grasim Industries"},
    {"symbol":"HDFCLIFE.NS",   "name":"HDFC Life Insurance"},
    {"symbol":"SBILIFE.NS",    "name":"SBI Life Insurance"},
    {"symbol":"INDUSINDBK.NS", "name":"IndusInd Bank"},
    {"symbol":"TATACONSUM.NS", "name":"Tata Consumer Products"},
    {"symbol":"BRITANNIA.NS",  "name":"Britannia Industries"},
    {"symbol":"NESTLEIND.NS",  "name":"Nestle India"},
    {"symbol":"HINDUNILVR.NS", "name":"Hindustan Unilever"},
    {"symbol":"COALINDIA.NS",  "name":"Coal India"},
    {"symbol":"BPCL.NS",       "name":"BPCL"},
    {"symbol":"TECHM.NS",      "name":"Tech Mahindra"},
    {"symbol":"LTF.NS",        "name":"L&T Finance"},
    {"symbol":"SHRIRAMFIN.NS", "name":"Shriram Finance"},
    {"symbol":"BEL.NS",        "name":"Bharat Electronics"},
]
NAMES  = [s["name"]   for s in NIFTY50]
N2S    = {s["name"]: s["symbol"] for s in NIFTY50}

PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a", family="Inter, sans-serif"),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(font=dict(color="#1e293b", size=12),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#e2e8f0", borderwidth=1),
)
AXIS_STYLE = dict(
    tickfont=dict(color="#1e293b", size=11, family="Inter, sans-serif"),
    title_font=dict(color="#0f172a", size=12, family="Inter, sans-serif"),
    linecolor="#cbd5e1", gridcolor="#f1f5f9", zerolinecolor="#cbd5e1",
)

def style_fig(fig):
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    return fig

def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (np.isnan(f) or np.isinf(f)) else f
    except Exception:
        return default

# ─ Sidebar ──────────────────────────────────────────────────────────
user = get_current_user()
name = user["full_name"] if user else "Guest"
try:
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/NSE_Logo.svg/200px-NSE_Logo.svg.png",
        width=110)
except Exception:
    pass
st.sidebar.markdown("<h3 style='color:#fff;margin:0 0 .4rem 0;font-size:1rem;'>News Sentiment</h3>",
                    unsafe_allow_html=True)
if user:
    st.sidebar.markdown(f"<span class='ui-badge badge-live'>👤 {name}</span>",
                        unsafe_allow_html=True)
    if st.sidebar.button("🚧 Sign Out", key="ns_logout"):
        logout(); st.rerun()
else:
    st.sidebar.markdown(
        "<span class='ui-badge badge-hist' style='background:rgba(255,255,255,.15);color:#e0e7ff!important;'>👤 Guest</span>",
        unsafe_allow_html=True)
    try:
        st.sidebar.page_link("pages/00_🔐_Login.py", label="🔐 Sign In")
    except Exception:
        pass
st.sidebar.markdown("---")
try:
    st.sidebar.page_link("app.py", label="🏠 Back to Main")
except Exception:
    pass
st.sidebar.caption("📊 Data: Yahoo Finance")
st.sidebar.caption("⚠️ Educational use only")

# ─ Hero ──────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">📰</div>
  <div>
    <div class="hero-title">News Sentiment Analyser</div>
    <div class="hero-sub">
      <span class='ui-badge badge-live'>LIVE</span>&nbsp;&nbsp;
      Analyse market mood from recent headlines
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if not TEXTBLOB_OK:
    st.error("❌ `textblob` not installed. Add it to requirements.txt and redeploy.")
    st.stop()

# ─ Controls ──────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([3, 1, 1])
with c1: ns_stock  = st.selectbox("🏛️ Select Company", NAMES, key="ns_stock")
with c2: ns_period = st.selectbox("📅 History Period", ["1mo","3mo","6mo"], key="ns_period")
with c3: max_news  = st.slider("📊 Headlines", 5, 30, 15, key="ns_max")

@st.cache_data(ttl=600)
def _ns_fetch(sym, period):
    try:
        t = yf.Ticker(sym)
        h = t.history(period=period, auto_adjust=True)
        if h is not None and not h.empty:
            h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
        try:
            n = t.news or []
        except Exception:
            n = []
        return h, n
    except Exception:
        return pd.DataFrame(), []

with st.spinner("🔍 Fetching price history & headlines…"):
    ns_hist, ns_news = _ns_fetch(N2S[ns_stock], ns_period)

# ─ Price strip ─────────────────────────────────────────────────────────
if not ns_hist.empty:
    try:
        # flatten MultiIndex if needed
        close_s = ns_hist["Close"]
        if isinstance(close_s, pd.DataFrame):
            close_s = close_s.iloc[:, 0]
        cp  = safe_float(close_s.iloc[-1])
        pp2 = safe_float(close_s.iloc[-2]) if len(close_s) > 1 else cp
        ch  = cp - pp2
        pt  = (ch / pp2 * 100) if pp2 else 0

        high_s = ns_hist["High"]
        if isinstance(high_s, pd.DataFrame): high_s = high_s.iloc[:, 0]
        low_s  = ns_hist["Low"]
        if isinstance(low_s, pd.DataFrame):  low_s  = low_s.iloc[:, 0]
        vol_s  = ns_hist["Volume"]
        if isinstance(vol_s, pd.DataFrame):  vol_s  = vol_s.iloc[:, 0]

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Price",        f"₹{cp:,.2f}")
        m2.metric("Change",       f"{ch:+.2f}",   delta=f"{pt:+.2f}%")
        m3.metric("Period High",  f"₹{safe_float(high_s.max()):,.2f}")
        m4.metric("Period Low",   f"₹{safe_float(low_s.min()):,.2f}")
        m5.metric("Avg Volume",   f"{int(vol_s.mean()):,}")

        st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(
            x=ns_hist.index, y=close_s,
            mode="lines", fill="tozeroy", name=ns_stock,
            line=dict(color="#6366f1", width=2),
            fillcolor="rgba(99,102,241,0.10)"
        ))
        fig_price.update_layout(
            **PLT_LAYOUT,
            title=f"{ns_stock} — Price History ({ns_period})",
            height=300, xaxis_title="Date", yaxis_title="Price (₹)"
        )
        style_fig(fig_price)
        st.plotly_chart(fig_price, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ Price chart error: {e}")
else:
    st.warning("⚠️ Could not fetch price data.")

# ─ Sentiment section ───────────────────────────────────────────────────
st.markdown("<p class='sec-label'>🧠 Headline Sentiment Analysis</p>", unsafe_allow_html=True)

if not ns_news:
    st.info("💬 No recent news found via Yahoo Finance for this stock.")
else:
    rows_ns = []
    for item in ns_news[:max_news]:
        try:
            if isinstance(item, dict):
                title = (
                    item.get("title")
                    or (item.get("content", {}) or {}).get("title", "")
                    or ""
                )
            else:
                title = str(item)
            title = title.strip()
            if not title:
                continue
            blob  = TextBlob(title)
            pol   = blob.sentiment.polarity
            sub   = blob.sentiment.subjectivity
            label = ("🟢 Positive" if pol > 0.1
                     else ("🔴 Negative" if pol < -0.1 else "⚪ Neutral"))
            rows_ns.append({
                "Headline":     title,
                "Sentiment":    label,
                "Polarity":     round(pol, 3),
                "Subjectivity": round(sub, 3),
            })
        except Exception:
            continue

    if not rows_ns:
        st.info("💬 Headlines fetched but none had readable text.")
    else:
        df_ns  = pd.DataFrame(rows_ns)
        pos_n  = len(df_ns[df_ns["Sentiment"] == "🟢 Positive"])
        neg_n  = len(df_ns[df_ns["Sentiment"] == "🔴 Negative"])
        neu_n  = len(df_ns[df_ns["Sentiment"] == "⚪ Neutral"])
        total  = pos_n + neg_n + neu_n

        # Headline KPI row
        ka, kb, kc, kd = st.columns(4)
        ka.metric("🟢 Positive",   pos_n)
        kb.metric("🔴 Negative",   neg_n)
        kc.metric("⚪ Neutral",    neu_n)
        avg_pol = round(df_ns["Polarity"].mean(), 3) if total else 0
        mood    = "🟢 Bullish" if avg_pol > 0.05 else ("🔴 Bearish" if avg_pol < -0.05 else "⚪ Neutral")
        kd.metric("Overall Mood",  mood, delta=str(avg_pol))

        st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

        # Charts
        ch1, ch2 = st.columns(2)

        with ch1:
            if total > 0:
                try:
                    fig_pie = px.pie(
                        values=[pos_n, neg_n, neu_n],
                        names=["🟢 Positive", "🔴 Negative", "⚪ Neutral"],
                        color_discrete_sequence=["#10b981", "#ef4444", "#9ca3af"],
                        title="Sentiment Distribution",
                        template="plotly_white", height=320)
                    fig_pie.update_layout(**PLT_LAYOUT)
                    st.plotly_chart(fig_pie, use_container_width=True)
                except Exception as e:
                    st.warning(f"⚠️ {e}")

        with ch2:
            try:
                fig_pol = px.histogram(
                    df_ns, x="Polarity", nbins=20,
                    color_discrete_sequence=["#6366f1"],
                    title="Polarity Distribution",
                    template="plotly_white", height=320,
                    labels={"Polarity": "Sentiment Polarity"})
                fig_pol.add_vline(x=0, line_dash="dash", line_color="#94a3b8")
                fig_pol.update_layout(**PLT_LAYOUT)
                style_fig(fig_pol)
                st.plotly_chart(fig_pol, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ {e}")

        # Polarity bar per headline
        try:
            df_bar = df_ns.copy()
            df_bar["Short"] = df_bar["Headline"].str[:55] + "…"
            fig_bar = px.bar(
                df_bar, x="Polarity", y="Short", orientation="h",
                color="Polarity",
                color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
                color_continuous_midpoint=0,
                title="Polarity per Headline",
                template="plotly_white", height=max(320, len(df_bar) * 28),
                labels={"Short": "", "Polarity": "Polarity"})
            fig_bar.update_layout(**PLT_LAYOUT, coloraxis_showscale=False,
                                  yaxis=dict(autorange="reversed"))
            style_fig(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Bar chart error: {e}")

        st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
        st.markdown("<p class='sec-label'>📝 All Headlines</p>", unsafe_allow_html=True)
        st.dataframe(df_ns, use_container_width=True, hide_index=True)
        st.caption("⚠️ Sentiment is computed from headline text only via TextBlob — not investment advice.")
