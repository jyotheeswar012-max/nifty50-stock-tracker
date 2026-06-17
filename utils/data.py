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

Importability note
------------------
When this module is imported outside a running Streamlit server (e.g. during
pytest), `@st.cache_data` is replaced with a transparent no-op decorator so
all public functions remain fully testable without a live Streamlit context.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Callable

import pandas as pd
import pytz
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from utils.constants import CACHE_TTL, NIFTY50, NSE_INDICES, SYMBOLS
from utils.logger import get_logger

log = get_logger(__name__)   # nse_tracker.utils.data

# ---------------------------------------------------------------------------
# Streamlit import guard
# When running inside Streamlit (app.py), st.cache_data caches results.
# When imported by pytest (no Streamlit context), cache_data is a no-op
# passthrough so the module can be imported and tested without errors.
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    # Probe whether the Streamlit runtime is actually active.
    # Outside a running app, st.runtime.exists() returns False.
    import streamlit.runtime
    _STREAMLIT_RUNNING = streamlit.runtime.exists()
except Exception:
    _STREAMLIT_RUNNING = False

if not _STREAMLIT_RUNNING:
    # Minimal no-op stand-ins used during testing
    class _FakeST:
        @staticmethod
        def cache_data(func=None, *, ttl=None, **_kwargs):
            """Passthrough decorator — no caching, no Streamlit dependency."""
            if func is not None:
                return func
            def decorator(f: Callable) -> Callable:
                return f
            return decorator

        class session_state:
            _store: dict = {}
            @classmethod
            def get(cls, key, default=None):
                return cls._store.get(key, default)
            def __class_getitem__(cls, key):
                return cls._store.get(key)

        @staticmethod
        def _session_state_set(key, value):
            _FakeST.session_state._store[key] = value

    st = _FakeST()  # type: ignore[assignment]
    # Patch session_state assignment used by _warn()
    _orig_set = _FakeST._session_state_set

# ---------------------------------------------------------------------------
# nselib availability check (optional dependency)
# ---------------------------------------------------------------------------
try:
    from nselib import capital_market as _cm
    NSELIB_OK = True
    log.info("nselib loaded successfully")
except Exception as _nselib_exc:
    NSELIB_OK = False
    log.warning("nselib not available (%s) — fallback source disabled", _nselib_exc)


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
            log.debug("Market check: Weekend")
            return False, "Weekend", lbl
        mo = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        mc = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if mo <= now <= mc:
            log.debug("Market check: Open at %s IST", now.strftime("%H:%M:%S"))
            return True, "Open", ""
        elif now < mo:
            lbl = "Last Close: " + (now - timedelta(days=1)).strftime("%d %b %Y, 3:30 PM IST")
            log.debug("Market check: Pre-Market")
            return False, "Pre-Market", lbl
        else:
            log.debug("Market check: Closed")
            return False, "Closed", "Last Close: " + now.strftime("%d %b %Y, 3:30 PM IST")
    except Exception as exc:
        log.error("is_nse_open() failed: %s", exc, exc_info=True)
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
    except Exception as exc:
        log.error("_clean_df() failed: %s", exc, exc_info=True)
        return pd.DataFrame()


def _clean_intraday_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise intraday: flatten MultiIndex cols, keep timezone."""
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        df = _flatten_cols(df.copy())
        return df
    except Exception as exc:
        log.error("_clean_intraday_df() failed: %s", exc, exc_info=True)
        return pd.DataFrame()


def _validate_ohlcv(df: pd.DataFrame) -> bool:
    """Return True if df has the required OHLCV columns and at least one row."""
    return (
        df is not None
        and not df.empty
        and {"Open", "High", "Low", "Close"}.issubset(df.columns)
    )


def _to_series(col: "pd.Series | pd.DataFrame") -> pd.Series:
    """Ensure a column extracted from a DataFrame is a 1-D Series.

    nselib occasionally returns duplicate column names after rename, which
    causes ``df[col_name]`` to return a DataFrame instead of a Series.
    Calling ``.str`` on a DataFrame raises AttributeError — this helper
    squeezes any accidental DataFrame down to the first Series.
    """
    if isinstance(col, pd.DataFrame):
        return col.iloc[:, 0]
    return col


# ---------------------------------------------------------------------------
# Source 1 — yfinance  (with exponential-backoff retry on rate-limit)
# ---------------------------------------------------------------------------

# Tracks the last time a successful yfinance request completed.
# Used to throttle inter-symbol delays when fetching 50 stocks.
_yf_last_ok: float = 0.0
_YF_MIN_INTERVAL = 0.5   # seconds between successful yfinance fetches
_YF_MAX_RETRIES  = 3


def _yf_history(symbol: str, period: str) -> pd.DataFrame:
    global _yf_last_ok
    # Throttle: ensure at least _YF_MIN_INTERVAL between requests.
    elapsed = time.monotonic() - _yf_last_ok
    if elapsed < _YF_MIN_INTERVAL:
        time.sleep(_YF_MIN_INTERVAL - elapsed)

    for attempt in range(_YF_MAX_RETRIES):
        try:
            log.debug("yfinance fetch: symbol=%s period=%s attempt=%d", symbol, period, attempt + 1)
            df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
            df = _clean_df(df)
            if _validate_ohlcv(df):
                log.debug("yfinance OK: symbol=%s rows=%d", symbol, len(df))
                _yf_last_ok = time.monotonic()
                return df
            log.warning("yfinance returned empty/invalid data: symbol=%s period=%s", symbol, period)
            return pd.DataFrame()
        except YFRateLimitError:
            wait = 2 ** attempt   # 1 s, 2 s, 4 s
            log.warning(
                "yfinance rate-limited: symbol=%s attempt=%d/%d — sleeping %ds",
                symbol, attempt + 1, _YF_MAX_RETRIES, wait,
            )
            time.sleep(wait)
        except Exception as exc:
            log.error("yfinance fetch failed: symbol=%s period=%s error=%s", symbol, period, exc, exc_info=True)
            return pd.DataFrame()

    log.error("yfinance fetch failed: symbol=%s period=%s error=Too Many Requests after %d retries", symbol, period, _YF_MAX_RETRIES)
    return pd.DataFrame()


def _yf_intraday(symbol: str, period: str = "1d", interval: str = "1m") -> pd.DataFrame:
    global _yf_last_ok
    elapsed = time.monotonic() - _yf_last_ok
    if elapsed < _YF_MIN_INTERVAL:
        time.sleep(_YF_MIN_INTERVAL - elapsed)

    for attempt in range(_YF_MAX_RETRIES):
        try:
            log.debug("yfinance intraday: symbol=%s period=%s interval=%s", symbol, period, interval)
            df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
            df = _clean_intraday_df(df)
            if _validate_ohlcv(df):
                log.debug("yfinance intraday OK: symbol=%s rows=%d", symbol, len(df))
                _yf_last_ok = time.monotonic()
                return df
            log.warning("yfinance intraday empty: symbol=%s", symbol)
            return pd.DataFrame()
        except YFRateLimitError:
            wait = 2 ** attempt
            log.warning("yfinance intraday rate-limited: symbol=%s attempt=%d — sleeping %ds", symbol, attempt + 1, wait)
            time.sleep(wait)
        except Exception as exc:
            log.error("yfinance intraday failed: symbol=%s error=%s", symbol, exc, exc_info=True)
            return pd.DataFrame()

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Source 2 — nselib  (official NSE India REST API)
# ---------------------------------------------------------------------------

def _nselib_history(symbol: str, period: str) -> pd.DataFrame:
    """
    Attempt to fetch historical OHLCV from nselib.
    nselib uses 'DD-MM-YYYY' date strings and strips '.NS' suffixes.

    Fix applied: nselib can return duplicate column names after rename,
    causing df[col] to yield a DataFrame instead of a Series.  Every
    numeric column is passed through _to_series() before calling .str.
    """
    if not NSELIB_OK:
        return pd.DataFrame()
    try:
        ticker   = symbol.replace(".NS", "").replace("^", "")
        days_map = {
            "1d": 2,   "5d": 7,  "1mo": 32, "3mo": 95,
            "6mo": 185, "1y": 366, "2y": 732, "5y": 1827,
        }
        lookback = days_map.get(period, 95)
        end   = datetime.now()
        start = end - timedelta(days=lookback)
        fmt   = "%d-%m-%Y"
        log.debug("nselib fetch: ticker=%s from=%s to=%s", ticker, start.strftime(fmt), end.strftime(fmt))

        raw = _cm.price_volume_and_deliverable_position_data(
            symbol=ticker,
            from_date=start.strftime(fmt),
            to_date=end.strftime(fmt),
        )
        if raw is None or raw.empty:
            log.warning("nselib returned empty: ticker=%s period=%s", ticker, period)
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
            log.error("nselib: no Date column after rename for ticker=%s; columns=%s", ticker, list(raw.columns))
            return pd.DataFrame()
        raw["Date"] = pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce")
        raw = raw.dropna(subset=["Date"]).set_index("Date").sort_index()

        # BUG FIX: duplicate column names after rename can produce a DataFrame
        # when you do raw[col], causing AttributeError on .str.  Always squeeze
        # to a Series via _to_series() before any string/numeric conversion.
        for col in ("Open", "High", "Low", "Close"):
            if col in raw.columns:
                series = _to_series(raw[col])
                raw[col] = pd.to_numeric(
                    series.astype(str).str.replace(",", "", regex=False),
                    errors="coerce",
                )
        if "Volume" in raw.columns:
            series = _to_series(raw["Volume"])
            raw["Volume"] = pd.to_numeric(
                series.astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ).fillna(0)

        df = _clean_df(raw)
        if _validate_ohlcv(df):
            log.info("nselib fallback used: symbol=%s rows=%d", symbol, len(df))
            return df
        log.warning("nselib data invalid after cleaning: symbol=%s", symbol)
    except Exception as exc:
        log.error("nselib fetch failed: symbol=%s period=%s error=%s", symbol, period, exc, exc_info=True)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Staleness guard helpers
# ---------------------------------------------------------------------------

_STALE_STORE: dict[str, pd.DataFrame] = {}


def _warn(msg: str) -> None:
    """Queue a warning to be displayed by app.py via session_state."""
    try:
        if _STREAMLIT_RUNNING:
            existing = st.session_state.get("data_warnings", [])
            if msg not in existing:
                st.session_state["data_warnings"] = existing + [msg]
    except Exception as exc:
        log.debug("_warn() could not write to session_state: %s", exc)


def _fetch_with_fallback(symbol: str, period: str) -> pd.DataFrame:
    """
    Core multi-source fetch used by all public cached functions.

    Order:
      1. yfinance primary  (with exponential-backoff retry on rate-limit)
      2. nselib fallback   (if yfinance returned empty)
      3. Stale cache       (if both live sources failed)
    """
    key = f"{symbol}:{period}"

    # --- Source 1: yfinance ---
    df = _yf_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        return df

    # --- Source 2: nselib ---
    log.warning("yfinance failed for %s/%s — trying nselib", symbol, period)
    df = _nselib_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        _warn(f"🔄 Using NSE backup source for **{symbol}** (Yahoo Finance unavailable)")
        return df

    # --- Source 3: stale cache ---
    log.error("Both live sources failed for %s/%s — checking stale cache", symbol, period)
    stale = _STALE_STORE.get(key)
    if stale is not None and not stale.empty:
        log.warning("Serving stale data for %s (age unknown)", symbol)
        _warn(f"⚠️ Serving **stale** data for {symbol} — both live sources failed")
        return stale

    log.error("No data available for %s/%s from any source", symbol, period)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Public cached fetch functions — import these in app.py
# (cache_data is a no-op when not running inside Streamlit)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Fetch daily OHLCV for one symbol (yfinance → nselib → stale cache)."""
    log.info("fetch_ticker called: symbol=%s period=%s", symbol, period)
    return _fetch_with_fallback(symbol, period)


@st.cache_data(ttl=CACHE_TTL)
def fetch_intraday(symbol: str) -> pd.DataFrame:
    """Fetch today's 1-minute bars (market-hours only, yfinance only)."""
    log.debug("fetch_intraday called: symbol=%s", symbol)
    return _yf_intraday(symbol, period="1d", interval="1m")


@st.cache_data(ttl=CACHE_TTL)
def fetch_indices() -> dict[str, pd.DataFrame]:
    """Fetch last-5-day daily bars for all NSE_INDICES."""
    log.info("fetch_indices called")
    result: dict[str, pd.DataFrame] = {}
    for idx in NSE_INDICES:
        df = _fetch_with_fallback(idx["symbol"], "5d")
        if not df.empty:
            result[idx["symbol"]] = df
        else:
            log.warning("fetch_indices: no data for %s", idx["symbol"])
    log.info("fetch_indices: loaded %d/%d indices", len(result), len(NSE_INDICES))
    return result


@st.cache_data(ttl=CACHE_TTL)
def fetch_all_stocks_5d() -> dict[str, pd.DataFrame]:
    """Fetch last-5-day daily bars for all 50 Nifty stocks."""
    log.info("fetch_all_stocks_5d called")
    result: dict[str, pd.DataFrame] = {}
    failed: list[str] = []
    for s in NIFTY50:
        df = _fetch_with_fallback(s["symbol"], "5d")
        if not df.empty:
            result[s["symbol"]] = df
        else:
            failed.append(s["symbol"])
    if failed:
        log.warning("fetch_all_stocks_5d: no data for %d symbols: %s", len(failed), failed)
    log.info("fetch_all_stocks_5d: loaded %d/50 symbols", len(result))
    return result


@st.cache_data(ttl=3600)
def fetch_all_history() -> dict[str, pd.DataFrame]:
    """Fetch 5-year daily bars for all 50 stocks + macro symbols (Time Machine)."""
    log.info("fetch_all_history called (heavy fetch, TTL=3600s)")
    result: dict[str, pd.DataFrame] = {}
    all_syms = SYMBOLS + ["USDINR=X", "CL=F", "GC=F", "^NSEI"]
    failed: list[str] = []
    for sym in all_syms:
        df = _fetch_with_fallback(sym, "5y")
        if not df.empty:
            result[sym] = df
        else:
            failed.append(sym)
    if failed:
        log.warning("fetch_all_history: no data for %d symbols: %s", len(failed), failed)
    log.info("fetch_all_history: loaded %d/%d symbols", len(result), len(all_syms))
    return result


@st.cache_data(ttl=60)
def get_source_status() -> dict[str, str]:
    """Return live status of each data source: 'ok' | 'degraded' | 'down'."""
    log.info("get_source_status probe running")
    status: dict[str, str] = {}
    try:
        df = _yf_history("^NSEI", "5d")
        status["yfinance"] = "ok" if not df.empty else "degraded"
    except Exception as exc:
        log.error("yfinance health probe failed: %s", exc, exc_info=True)
        status["yfinance"] = "down"

    if NSELIB_OK:
        try:
            df = _nselib_history("RELIANCE.NS", "5d")
            status["nselib"] = "ok" if not df.empty else "degraded"
        except Exception as exc:
            log.error("nselib health probe failed: %s", exc, exc_info=True)
            status["nselib"] = "down"
    else:
        status["nselib"] = "not installed"

    log.info("get_source_status result: %s", status)
    return status
