import streamlit as st
from utils.supabase_auth import require_login

st.set_page_config(page_title="News Sentiment", page_icon="📰", layout="wide")
user = require_login()

# ---- original news page content below ----
import requests
import pandas as pd
from datetime import datetime
import pytz
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

st.title("📰 News & Sentiment")
st.caption(f"Signed in as **{user['full_name']}**")

try:
    from newsapi import NewsApiClient
    api_key = st.secrets.get("newsapi", {}).get("key", "")
    if not api_key:
        raise ValueError("No NewsAPI key")
    newsapi = NewsApiClient(api_key=api_key)

    selected = st.selectbox("Select Stock", NIFTY50_NAMES)
    if st.button("🔍 Fetch News"):
        with st.spinner("Fetching articles..."):
            res = newsapi.get_everything(
                q=selected, language="en", sort_by="publishedAt", page_size=10
            )
        articles = res.get("articles", [])
        if not articles:
            st.info("No recent news found.")
        else:
            for a in articles:
                with st.container(border=True):
                    st.markdown(f"**[{a['title']}]({a['url']})**")
                    st.caption(f"{a.get('source',{}).get('name','')} • {a.get('publishedAt','')[:10]}")
                    if a.get('description'):
                        st.write(a['description'])
except Exception as e:
    st.info("💡 Add a NewsAPI key in Streamlit Secrets under `[newsapi] key = 'your_key'` to enable this page.")
    st.caption(f"Get a free key at [newsapi.org](https://newsapi.org). Error: {e}")
