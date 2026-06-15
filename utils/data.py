"""Data fetching helpers (yfinance wrappers + market-state detection).

All @st.cache_data decorators live here so caching is co-located with
the fetch logic.  app.py imports the cached functions directly.
"""
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz

from utils.constants import NIFTY50, SYMBOLS, NSE_INDICES, CACHE_TTL


# ---------------------------------------------------------------------------
# Market-hours detection
# ---------------------------------------------------------------------------

def is_nse_open():
    """Return (is_open: bool, status_label: str, last_close_label: str)."""
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        if now.weekday() >= 5:
            lbl = "Last Close: Fri " + (now - timedelta(days=now.weekday() - 4)).strftime("%d %b %Y, 3:30 PM")
            return False, "Weekend", lbl
        mo = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        mc = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if mo <= now <= mc:
            return True, "Open", ""
        elif now < mo:
            lbl = "Last Close: " + (now - timedelta(days=1)).strftime("%d %b %Y, 3:30 PM IST")
            return False, "Pre-Market", lbl
        else:
            return False, "Closed", "Last Close: " + now.strftime("%d %b %Y, 3:30 PM IST")
    except Exception:
        return False, "Unknown", ""


# ---------------------------------------------------------------------------
# Low-level yfinance helpers (not cached — called by cached wrappers below)
# ---------------------------------------------------------------------------

def _clean_df(df):
    """Normalise daily OHLCV DataFrame: flatten MultiIndex cols, strip tz."""
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            lvl0 = list(df.columns.get_level_values(0))
            df.columns = lvl0 if {"Open","High","Low","Close","Volume"}.intersection(lvl0) \
                         else list(df.columns.get_level_values(1))
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = pd.to_datetime(df.index).normalize()
        return df
    except Exception:
        return pd.DataFrame()


def _clean_intraday_df(df):
    """Normalise intraday DataFrame: flatten MultiIndex cols, keep tz."""
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            lvl0 = list(df.columns.get_level_values(0))
            df.columns = lvl0 if {"Open","High","Low","Close","Volume"}.intersection(lvl0) \
                         else list(df.columns.get_level_values(1))
        return df
    except Exception:
        return pd.DataFrame()


def _ticker_history(symbol, period):
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        if df is not None and not df.empty:
            return _clean_df(df)
    except Exception:
        pass
    return pd.DataFrame()


def _ticker_intraday(symbol, period="1d", interval="1m"):
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if df is not None and not df.empty:
            return _clean_intraday_df(df)
    except Exception:
        pass
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Cached fetch functions — import these in app.py
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def fetch_ticker(symbol, period="3mo"):
    """Fetch daily OHLCV history for one symbol."""
    return _ticker_history(symbol, period)


@st.cache_data(ttl=CACHE_TTL)
def fetch_intraday(symbol):
    """Fetch today's 1-minute bars (empty when market is closed)."""
    return _ticker_intraday(symbol, period="1d", interval="1m")


@st.cache_data(ttl=CACHE_TTL)
def fetch_indices():
    """Fetch last-5-day daily bars for all NSE_INDICES."""
    result = {}
    for idx in NSE_INDICES:
        try:
            df = _ticker_history(idx["symbol"], "5d")
            if not df.empty:
                result[idx["symbol"]] = df
        except Exception:
            pass
    return result


@st.cache_data(ttl=CACHE_TTL)
def fetch_all_stocks_5d():
    """Fetch last-5-day daily bars for all 50 Nifty stocks."""
    result = {}
    for s in NIFTY50:
        try:
            df = _ticker_history(s["symbol"], "5d")
            if not df.empty:
                result[s["symbol"]] = df
        except Exception:
            pass
    return result


@st.cache_data(ttl=3600)
def fetch_all_history():
    """Fetch 5-year daily bars for all stocks + macro symbols (Time Machine)."""
    result = {}
    for sym in SYMBOLS + ["USDINR=X", "CL=F", "GC=F", "^NSEI"]:
        try:
            df = _ticker_history(sym, "5y")
            if not df.empty:
                result[sym] = df
        except Exception:
            pass
    return result
