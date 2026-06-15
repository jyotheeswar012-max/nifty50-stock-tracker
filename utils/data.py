"""Data fetching helpers with multi-source fallback.

Fetch priority
--------------
1. yfinance  — primary (global CDN, battle-tested, supports OHLCV + intraday)
2. nselib    — fallback (official NSE India REST API, no auth required)
3. Stale-cache guard — if both fail and a previous result exists, serve it
                       with a visible staleness warning surfaced via
                       st.session_state["data_warnings"].

All @st.cache_data decorators live here so caching is co-located with
the fetch logic.  app.py imports only the cached public functions.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

from utils.constants import CACHE_TTL, NIFTY50, NSE_INDICES, SYMBOLS

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# nselib availability check (optional dependency)
# ---------------------------------------------------------------------------
try:
    from nselib import capital_market as _cm
    NSELIB_OK = True
except Exception:
    NSELIB_OK = False


# ---------------------------------------------------------------------------
# Market-hours detection
# ---------------------------------------------------------------------------

def is_nse_open() -> tuple[bool, str, str]:
    """Return (is_open, status_label, last_close_label)."""
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
# DataFrame normalisation helpers (private)
# ---------------------------------------------------------------------------

def _flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns produced by yfinance batch downloads."""
    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = list(df.columns.get_level_values(0))
        df.columns = (
            lvl0
            if {"Open", "High", "Low", "Close", "Volume"}.intersection(lvl0)
            else list(df.columns.get_level_values(1))
        )
    return df


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise daily OHLCV: flatten MultiIndex cols, strip timezone, normalize dates."""
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        df = _flatten_cols(df.copy())
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = pd.to_datetime(df.index).normalize()
        return df
    except Exception:
        return pd.DataFrame()


def _clean_intraday_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise intraday: flatten MultiIndex cols, keep timezone."""
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        df = _flatten_cols(df.copy())
        return df
    except Exception:
        return pd.DataFrame()


def _validate_ohlcv(df: pd.DataFrame) -> bool:
    """Return True if df has the required OHLCV columns and at least one row."""
    return (
        df is not None
        and not df.empty
        and {"Open", "High", "Low", "Close"}.issubset(df.columns)
    )


# ---------------------------------------------------------------------------
# Source 1 — yfinance
# ---------------------------------------------------------------------------

def _yf_history(symbol: str, period: str) -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        df = _clean_df(df)
        if _validate_ohlcv(df):
            return df
    except Exception as exc:
        log.debug("yfinance daily failed [%s/%s]: %s", symbol, period, exc)
    return pd.DataFrame()


def _yf_intraday(symbol: str, period: str = "1d", interval: str = "1m") -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        df = _clean_intraday_df(df)
        if _validate_ohlcv(df):
            return df
    except Exception as exc:
        log.debug("yfinance intraday failed [%s]: %s", symbol, exc)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Source 2 — nselib  (official NSE India REST API)
# ---------------------------------------------------------------------------

def _nselib_history(symbol: str, period: str) -> pd.DataFrame:
    """
    Attempt to fetch historical OHLCV from nselib.

    nselib uses 'DD-MM-YYYY' date strings and strips '.NS' suffixes.
    Supported periods are translated to calendar lookbacks.
    """
    if not NSELIB_OK:
        return pd.DataFrame()
    try:
        # Strip .NS suffix and map period -> start date
        ticker   = symbol.replace(".NS", "").replace("^", "")
        days_map = {
            "1d": 2,   "5d": 7,  "1mo": 32, "3mo": 95,
            "6mo": 185, "1y": 366, "2y": 732, "5y": 1827,
        }
        lookback = days_map.get(period, 95)
        end      = datetime.now()
        start    = end - timedelta(days=lookback)
        fmt      = "%d-%m-%Y"

        raw = _cm.price_volume_and_deliverable_position_data(
            symbol=ticker,
            from_date=start.strftime(fmt),
            to_date=end.strftime(fmt),
        )
        if raw is None or raw.empty:
            return pd.DataFrame()

        # Normalise column names  (nselib uses mixed case & spaces)
        raw.columns = raw.columns.str.strip()
        col_map = {
            c: "Open"   for c in raw.columns if "open"   in c.lower()
        } | {
            c: "High"   for c in raw.columns if "high"   in c.lower()
        } | {
            c: "Low"    for c in raw.columns if "low"    in c.lower()
        } | {
            c: "Close"  for c in raw.columns if "close"  in c.lower() or "ltp" in c.lower()
        } | {
            c: "Volume" for c in raw.columns if "volume" in c.lower() or "ttl" in c.lower()
        } | {
            c: "Date"   for c in raw.columns if "date"   in c.lower()
        }
        raw = raw.rename(columns=col_map)
        if "Date" not in raw.columns:
            return pd.DataFrame()
        raw["Date"] = pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce")
        raw = raw.dropna(subset=["Date"]).set_index("Date").sort_index()
        for col in ("Open", "High", "Low", "Close"):
            if col in raw.columns:
                raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(",", ""), errors="coerce")
        if "Volume" in raw.columns:
            raw["Volume"] = pd.to_numeric(raw["Volume"].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df = _clean_df(raw)
        if _validate_ohlcv(df):
            log.info("nselib fallback used for %s", symbol)
            return df
    except Exception as exc:
        log.debug("nselib failed [%s/%s]: %s", symbol, period, exc)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Staleness guard helpers
# ---------------------------------------------------------------------------

_STALE_STORE: dict[str, pd.DataFrame] = {}


def _warn(msg: str) -> None:
    """Queue a warning to be displayed by app.py via session_state."""
    try:
        existing = st.session_state.get("data_warnings", [])
        if msg not in existing:
            st.session_state["data_warnings"] = existing + [msg]
    except Exception:
        pass


def _fetch_with_fallback(symbol: str, period: str) -> pd.DataFrame:
    """
    Core multi-source fetch used by all public cached functions.

    Order:
      1. yfinance primary
      2. nselib fallback  (if yfinance returned empty)
      3. Stale cache      (if both live sources failed)
    """
    key = f"{symbol}:{period}"

    # --- Source 1: yfinance ---
    df = _yf_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df          # update stale-cache on success
        return df

    # --- Source 2: nselib ---
    df = _nselib_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        _warn(f"🔄 Using NSE backup source for **{symbol}** (Yahoo Finance unavailable)")
        return df

    # --- Source 3: stale cache ---
    stale = _STALE_STORE.get(key)
    if stale is not None and not stale.empty:
        _warn(f"⚠️ Serving **stale** data for {symbol} — both live sources failed")
        return stale

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Public cached fetch functions — import these in app.py
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Fetch daily OHLCV for one symbol (yfinance → nselib → stale cache)."""
    return _fetch_with_fallback(symbol, period)


@st.cache_data(ttl=CACHE_TTL)
def fetch_intraday(symbol: str) -> pd.DataFrame:
    """Fetch today's 1-minute bars (market-hours only, yfinance only)."""
    return _yf_intraday(symbol, period="1d", interval="1m")


@st.cache_data(ttl=CACHE_TTL)
def fetch_indices() -> dict[str, pd.DataFrame]:
    """Fetch last-5-day daily bars for all NSE_INDICES."""
    result: dict[str, pd.DataFrame] = {}
    for idx in NSE_INDICES:
        df = _fetch_with_fallback(idx["symbol"], "5d")
        if not df.empty:
            result[idx["symbol"]] = df
    return result


@st.cache_data(ttl=CACHE_TTL)
def fetch_all_stocks_5d() -> dict[str, pd.DataFrame]:
    """Fetch last-5-day daily bars for all 50 Nifty stocks."""
    result: dict[str, pd.DataFrame] = {}
    for s in NIFTY50:
        df = _fetch_with_fallback(s["symbol"], "5d")
        if not df.empty:
            result[s["symbol"]] = df
    return result


@st.cache_data(ttl=3600)
def fetch_all_history() -> dict[str, pd.DataFrame]:
    """Fetch 5-year daily bars for all 50 stocks + macro symbols (Time Machine)."""
    result: dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS + ["USDINR=X", "CL=F", "GC=F", "^NSEI"]:
        df = _fetch_with_fallback(sym, "5y")
        if not df.empty:
            result[sym] = df
    return result


# ---------------------------------------------------------------------------
# Source health-check — used by app.py to show the data source badge
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def get_source_status() -> dict[str, str]:
    """
    Return a dict reporting the live status of each data source.

    Keys: "yfinance", "nselib"
    Values: "ok" | "degraded" | "down"
    """
    status: dict[str, str] = {}

    # Probe yfinance with a tiny 5d fetch of Nifty
    try:
        df = _yf_history("^NSEI", "5d")
        status["yfinance"] = "ok" if not df.empty else "degraded"
    except Exception:
        status["yfinance"] = "down"

    # Probe nselib
    if NSELIB_OK:
        try:
            df = _nselib_history("RELIANCE.NS", "5d")
            status["nselib"] = "ok" if not df.empty else "degraded"
        except Exception:
            status["nselib"] = "down"
    else:
        status["nselib"] = "not installed"

    return status
