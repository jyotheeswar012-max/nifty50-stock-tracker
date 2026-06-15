"""Data fetching helpers with multi-source fallback + structured logging.

Fetch priority
--------------
1. yfinance  — primary (global CDN, battle-tested, OHLCV + intraday)
2. nselib    — fallback (official NSE India REST API, no auth)
3. Stale-cache guard — if both fail and a previous result exists, serve it
                       with a warning queued in st.session_state["data_warnings"].
"""
from __future__ import annotations

import functools
import time
from datetime import datetime, timedelta

import pandas as pd
import pytz
import streamlit as st
import yfinance as yf

from utils.constants import CACHE_TTL, NIFTY50, NSE_INDICES, SYMBOLS
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# nselib availability check (optional dependency)
# ---------------------------------------------------------------------------
try:
    from nselib import capital_market as _cm
    NSELIB_OK = True
    log.info("nselib loaded successfully — fallback source available")
except Exception as _nselib_exc:
    NSELIB_OK = False
    log.warning("nselib not available (%s) — yfinance-only mode", _nselib_exc)


# ---------------------------------------------------------------------------
# Timing decorator (for profiling slow fetches in logs)
# ---------------------------------------------------------------------------

def _timed(fn):
    """Log execution time of any fetch function at DEBUG level."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        t0     = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        log.debug("%s(%s) completed in %.1f ms", fn.__name__, args[:2], elapsed)
        return result
    return wrapper


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
            log.info("Market status: Weekend")
            return False, "Weekend", lbl
        mo = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        mc = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if mo <= now <= mc:
            log.info("Market status: OPEN at %s IST", now.strftime("%H:%M:%S"))
            return True, "Open", ""
        elif now < mo:
            lbl = "Last Close: " + (now - timedelta(days=1)).strftime("%d %b %Y, 3:30 PM IST")
            log.info("Market status: Pre-Market")
            return False, "Pre-Market", lbl
        else:
            log.info("Market status: Closed")
            return False, "Closed", "Last Close: " + now.strftime("%d %b %Y, 3:30 PM IST")
    except Exception as exc:
        log.error("is_nse_open() failed: %s", exc, exc_info=True)
        return False, "Unknown", ""


# ---------------------------------------------------------------------------
# DataFrame normalisation helpers (private)
# ---------------------------------------------------------------------------

def _flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = list(df.columns.get_level_values(0))
        df.columns = (
            lvl0
            if {"Open", "High", "Low", "Close", "Volume"}.intersection(lvl0)
            else list(df.columns.get_level_values(1))
        )
    return df


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        df = _flatten_cols(df.copy())
        if hasattr(df.index, "tz") and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = pd.to_datetime(df.index).normalize()
        return df
    except Exception as exc:
        log.error("_clean_df failed: %s", exc, exc_info=True)
        return pd.DataFrame()


def _clean_intraday_df(df: pd.DataFrame) -> pd.DataFrame:
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        df = _flatten_cols(df.copy())
        return df
    except Exception as exc:
        log.error("_clean_intraday_df failed: %s", exc, exc_info=True)
        return pd.DataFrame()


def _validate_ohlcv(df: pd.DataFrame) -> bool:
    return (
        df is not None
        and not df.empty
        and {"Open", "High", "Low", "Close"}.issubset(df.columns)
    )


# ---------------------------------------------------------------------------
# Source 1 — yfinance
# ---------------------------------------------------------------------------

@_timed
def _yf_history(symbol: str, period: str) -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        df = _clean_df(df)
        if _validate_ohlcv(df):
            log.info("yfinance OK  | %s | period=%s | rows=%d", symbol, period, len(df))
            return df
        log.warning("yfinance returned empty/invalid frame for %s [period=%s]", symbol, period)
    except Exception as exc:
        log.error("yfinance FAILED | %s | period=%s | %s", symbol, period, exc)
    return pd.DataFrame()


@_timed
def _yf_intraday(symbol: str, period: str = "1d", interval: str = "1m") -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        df = _clean_intraday_df(df)
        if _validate_ohlcv(df):
            log.info("yfinance intraday OK | %s | rows=%d", symbol, len(df))
            return df
        log.warning("yfinance intraday empty for %s", symbol)
    except Exception as exc:
        log.error("yfinance intraday FAILED | %s | %s", symbol, exc)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Source 2 — nselib  (official NSE India REST API)
# ---------------------------------------------------------------------------

@_timed
def _nselib_history(symbol: str, period: str) -> pd.DataFrame:
    if not NSELIB_OK:
        return pd.DataFrame()
    try:
        ticker   = symbol.replace(".NS", "").replace("^", "")
        days_map = {
            "1d": 2, "5d": 7, "1mo": 32, "3mo": 95,
            "6mo": 185, "1y": 366, "2y": 732, "5y": 1827,
        }
        lookback = days_map.get(period, 95)
        end      = datetime.now()
        start    = end - timedelta(days=lookback)
        fmt      = "%d-%m-%Y"

        log.info("nselib fetch | %s | %s → %s", ticker, start.strftime(fmt), end.strftime(fmt))
        raw = _cm.price_volume_and_deliverable_position_data(
            symbol=ticker,
            from_date=start.strftime(fmt),
            to_date=end.strftime(fmt),
        )
        if raw is None or raw.empty:
            log.warning("nselib returned empty frame for %s", ticker)
            return pd.DataFrame()

        raw.columns = raw.columns.str.strip()
        col_map = (
            {c: "Open"   for c in raw.columns if "open"   in c.lower()} |
            {c: "High"   for c in raw.columns if "high"   in c.lower()} |
            {c: "Low"    for c in raw.columns if "low"    in c.lower()} |
            {c: "Close"  for c in raw.columns if "close"  in c.lower() or "ltp" in c.lower()} |
            {c: "Volume" for c in raw.columns if "volume" in c.lower() or "ttl" in c.lower()} |
            {c: "Date"   for c in raw.columns if "date"   in c.lower()}
        )
        raw = raw.rename(columns=col_map)
        if "Date" not in raw.columns:
            log.error("nselib frame for %s has no Date column — columns: %s", ticker, list(raw.columns))
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
            log.info("nselib OK (fallback) | %s | rows=%d", symbol, len(df))
            return df
        log.warning("nselib frame invalid after cleaning for %s", symbol)
    except Exception as exc:
        log.error("nselib FAILED | %s | period=%s | %s", symbol, period, exc, exc_info=True)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Staleness guard
# ---------------------------------------------------------------------------

_STALE_STORE: dict[str, pd.DataFrame] = {}


def _warn(msg: str) -> None:
    try:
        existing = st.session_state.get("data_warnings", [])
        if msg not in existing:
            st.session_state["data_warnings"] = existing + [msg]
    except Exception:
        pass


def _fetch_with_fallback(symbol: str, period: str) -> pd.DataFrame:
    """3-tier fetch: yfinance → nselib → stale-cache."""
    key = f"{symbol}:{period}"

    df = _yf_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        return df

    log.warning("yfinance unavailable for %s — trying nselib fallback", symbol)
    df = _nselib_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        _warn(f"\U0001f504 Using NSE backup source for **{symbol}** (Yahoo Finance unavailable)")
        return df

    stale = _STALE_STORE.get(key)
    if stale is not None and not stale.empty:
        log.warning("Both sources failed for %s — serving STALE data from cache", symbol)
        _warn(f"\u26a0\ufe0f Serving **stale** data for {symbol} \u2014 both live sources failed")
        return stale

    log.error("All data sources failed for %s [period=%s] — returning empty DataFrame", symbol, period)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Public cached fetch functions
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Fetch daily OHLCV (yfinance → nselib → stale)."""
    return _fetch_with_fallback(symbol, period)


@st.cache_data(ttl=CACHE_TTL)
def fetch_intraday(symbol: str) -> pd.DataFrame:
    """Fetch today's 1-minute bars (yfinance only)."""
    return _yf_intraday(symbol, period="1d", interval="1m")


@st.cache_data(ttl=CACHE_TTL)
def fetch_indices() -> dict[str, pd.DataFrame]:
    """Fetch last-5-day bars for all NSE_INDICES."""
    log.info("fetch_indices() called — fetching %d indices", len(NSE_INDICES))
    result: dict[str, pd.DataFrame] = {}
    for idx in NSE_INDICES:
        df = _fetch_with_fallback(idx["symbol"], "5d")
        if not df.empty:
            result[idx["symbol"]] = df
    log.info("fetch_indices() returned %d/%d indices", len(result), len(NSE_INDICES))
    return result


@st.cache_data(ttl=CACHE_TTL)
def fetch_all_stocks_5d() -> dict[str, pd.DataFrame]:
    """Fetch last-5-day bars for all 50 Nifty stocks."""
    log.info("fetch_all_stocks_5d() called")
    result: dict[str, pd.DataFrame] = {}
    for s in NIFTY50:
        df = _fetch_with_fallback(s["symbol"], "5d")
        if not df.empty:
            result[s["symbol"]] = df
    log.info("fetch_all_stocks_5d() returned %d/50 stocks", len(result))
    return result


@st.cache_data(ttl=3600)
def fetch_all_history() -> dict[str, pd.DataFrame]:
    """Fetch 5-year bars for all stocks + macro (Time Machine)."""
    log.info("fetch_all_history() called — heavy call, ttl=3600s")
    result: dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS + ["USDINR=X", "CL=F", "GC=F", "^NSEI"]:
        df = _fetch_with_fallback(sym, "5y")
        if not df.empty:
            result[sym] = df
    log.info("fetch_all_history() returned %d symbols", len(result))
    return result


@st.cache_data(ttl=60)
def get_source_status() -> dict[str, str]:
    """Live health check for each data source."""
    status: dict[str, str] = {}
    try:
        df = _yf_history("^NSEI", "5d")
        status["yfinance"] = "ok" if not df.empty else "degraded"
    except Exception as exc:
        log.error("yfinance health-check failed: %s", exc)
        status["yfinance"] = "down"

    if NSELIB_OK:
        try:
            df = _nselib_history("RELIANCE.NS", "5d")
            status["nselib"] = "ok" if not df.empty else "degraded"
        except Exception as exc:
            log.error("nselib health-check failed: %s", exc)
            status["nselib"] = "down"
    else:
        status["nselib"] = "not installed"

    log.info("Source status: %s", status)
    return status
