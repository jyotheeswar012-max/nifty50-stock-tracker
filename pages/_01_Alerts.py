# Renamed from 01_Alerts.py — leading underscore prevents Streamlit page registration.
# Content preserved intact below.
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Price Alerts", page_icon="\U0001f514", layout="wide", initial_sidebar_state="collapsed")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    def inject_topbar(user=None): pass

try:
    from utils.supabase_auth import get_current_user, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def is_guest(): return True
    def login_nudge(msg=""): st.info("Sign in to save your data.")

try:
    from utils.notifications import send_email, smtp_configured
except Exception:
    def send_email(to, subject, body): return False, "notifications module unavailable"
    def smtp_configured(): return False

user = get_current_user()
try:
    inject_topbar(user=user)
except Exception:
    pass

NIFTY50 = [
    {"symbol":"RELIANCE.NS","name":"Reliance Industries"},
    {"symbol":"HDFCBANK.NS","name":"HDFC Bank"},
    {"symbol":"ICICIBANK.NS","name":"ICICI Bank"},
    {"symbol":"INFY.NS","name":"Infosys"},
    {"symbol":"TCS.NS","name":"TCS"},
]
N2S = {s["name"]: s["symbol"] for s in NIFTY50}
NAMES = [s["name"] for s in NIFTY50]
IST = pytz.timezone("Asia/Kolkata")

st.write("This page is disabled. Use the main app instead.")
