"""
Page: News Sentiment Analysis. No login required.
"""
import streamlit as st
from utils.supabase_auth import get_current_user, is_guest

st.set_page_config(page_title="News Sentiment", page_icon="💰", layout="wide")
user  = get_current_user()
guest = is_guest()

import pandas as pd
import plotly.express as px
import warnings
warnings.filterwarnings("ignore")

try:
    from textblob import TextBlob
    TEXTBLOB_OK = True
except ImportError:
    TEXTBLOB_OK = False

NIFTY50_NAMES = [
    "Reliance Industries","HDFC Bank","ICICI Bank","Infosys","TCS",
    "Bharti Airtel","ITC","Kotak Mahindra Bank","Larsen & Toubro","HCL Technologies",
    "Axis Bank","State Bank of India","Bajaj Finance","Wipro","Asian Paints",
    "Maruti Suzuki","Sun Pharmaceutical","Titan Company","UltraTech Cement","ONGC",
]

def classify(score: float) -> tuple[str, str]:
    if score > 0.05:  return "Positive", "🟢"
    if score < -0.05: return "Negative", "🔴"
    return "Neutral", "⚪"

st.title("💰 News Sentiment Analyser")
if guest:
    st.caption("👤 Browsing as **Guest** — sentiment analysis available to all")
else:
    st.caption(f"Signed in as **{user['full_name']}**")

if not TEXTBLOB_OK:
    st.error("❌ `textblob` not installed. Add `textblob>=0.18.0` to requirements.txt and run `python -m textblob.download_corpora`.")
    st.stop()

tabs = st.tabs(["📰 Analyse Headlines", "✏️ Demo — Paste Text"])

# ─ Tab 1: News headlines ─────────────────────────────────────────────────
with tabs[0]:
    st.subheader("📰 Paste News Headlines")
    st.caption("Paste one headline per line. Sentiment is scored using TextBlob NLP.")

    sel_stock = st.selectbox("Stock context (label only)", NIFTY50_NAMES, key="ns_stock")

    default_headlines = """Reliance Industries reports record quarterly profit
HDFC Bank faces regulatory scrutiny over loan practices
Infosys wins $1.5 billion deal with European client
Sensex falls 500 points amid global uncertainty
TCS announces 50,000 new hires for FY26"""

    raw_text = st.text_area(
        "Headlines (one per line)",
        value=default_headlines,
        height=180,
        key="ns_headlines",
    )

    if st.button("🔍 Analyse Sentiment", type="primary", key="ns_analyse"):
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        if not lines:
            st.warning("⚠️ Please enter at least one headline.")
        else:
            rows = []
            counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
            for line in lines:
                try:
                    blob  = TextBlob(line)
                    score = float(blob.sentiment.polarity)
                except Exception:
                    score = 0.0
                label, emoji = classify(score)
                counts[label] += 1
                rows.append({
                    "Headline":  line,
                    "Sentiment": f"{emoji} {label}",
                    "Score":     round(score, 3),
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Donut chart
            try:
                pie_df = pd.DataFrame([
                    {"Sentiment": k, "Count": v}
                    for k, v in counts.items() if v > 0
                ])
                fig = px.pie(
                    pie_df, names="Sentiment", values="Count", hole=0.5,
                    color="Sentiment",
                    color_discrete_map={
                        "Positive": "#00c853",
                        "Negative": "#ff1744",
                        "Neutral":  "#9e9e9e",
                    },
                    title=f"Sentiment Summary — {sel_stock}",
                    template="plotly_dark",
                )
                fig.update_layout(height=340)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"⚠️ Chart error: {e}")

            # Overall verdict
            avg = sum(r["Score"] for r in rows) / len(rows)
            vlabel, vemoji = classify(avg)
            color = "green" if vlabel == "Positive" else ("red" if vlabel == "Negative" else "gray")
            st.markdown(
                f"<div style='text-align:center; padding:1rem; border-radius:10px; "
                f"background:rgba(255,255,255,.05); font-size:1.3rem; font-weight:700;'>"
                f"{vemoji} Overall: <span style='color:{color};'>{vlabel}</span> "
                f"(avg score: {avg:+.3f})</div>",
                unsafe_allow_html=True,
            )

# ─ Tab 2: Live demo ───────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("✏️ Live Text Sentiment Demo")
    st.caption("Type or paste any text to test the sentiment engine instantly.")
    demo_text = st.text_area(
        "Your text",
        value="The stock market is showing strong bullish signals today.",
        height=120,
        key="ns_demo",
    )
    if demo_text.strip():
        try:
            blob  = TextBlob(demo_text.strip())
            score = float(blob.sentiment.polarity)
            subj  = float(blob.sentiment.subjectivity)
            label, emoji = classify(score)
            d1, d2, d3 = st.columns(3)
            d1.metric("Sentiment",     f"{emoji} {label}")
            d2.metric("Polarity",      f"{score:+.3f}")
            d3.metric("Subjectivity",  f"{subj:.3f}")
        except Exception as e:
            st.warning(f"⚠️ Analysis error: {e}")
