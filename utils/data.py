"""Data fetching helpers with multi-source fallback.

Fetch priority
--------------
1. yfinance batch (yf.download all 50 at once) — primary, fastest
2. yfinance single (per-symbol fallback for any that failed the batch)
3. nselib    — fallback (official NSE India REST API, no auth required)
4. Stale-cache guard — if all sources fail, serve previous result with warning

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
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    import streamlit.runtime
    _STREAMLIT_RUNNING = streamlit.runtime.exists()
except Exception:
    _STREAMLIT_RUNNING = False

if not _STREAMLIT_RUNNING:
    class _FakeST:
        @staticmethod
        def cache_data(func=None, *, ttl=None, **_kwargs):
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
    try:
        if df is None or df.empty:
            return pd.DataFrame()
        df = _flatten_cols(df.copy())
        return df
    except Exception as exc:
        log.error("_clean_intraday_df() failed: %s", exc, exc_info=True)
        return pd.DataFrame()


def _validate_ohlcv(df: pd.DataFrame) -> bool:
    return (
        df is not None
        and not df.empty
        and {"Open", "High", "Low", "Close"}.issubset(df.columns)
    )


def _to_series(col: "pd.Series | pd.DataFrame") -> pd.Series:
    """Squeeze a possible DataFrame (duplicate col names) to a Series."""
    if isinstance(col, pd.DataFrame):
        return col.iloc[:, 0]
    return col


# ---------------------------------------------------------------------------
# Source 1a — yfinance BATCH download  (all symbols in ONE HTTP request)
# ---------------------------------------------------------------------------

def _yf_batch_download(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV for all symbols in a single yf.download() call.
    Returns a dict {symbol: DataFrame}.  Symbols that come back empty
    are omitted so the caller can fall back individually.

    This replaces 50 serial HTTP requests with 1, reducing wall-clock
    time from ~25 s to ~2–3 s.
    """
    result: dict[str, pd.DataFrame] = {}
    if not symbols:
        return result
    try:
        log.info("yf.download batch: %d symbols period=%s", len(symbols), period)
        t0 = time.monotonic()
        raw = yf.download(
            tickers=symbols,
            period=period,
            auto_adjust=True,
            group_by="ticker",   # MultiIndex: (OHLCV, symbol)
            progress=False,
            threads=True,        # yfinance uses thread pool internally
            timeout=30,
        )
        elapsed = time.monotonic() - t0
        log.info("yf.download batch finished in %.1fs", elapsed)

        if raw.empty:
            log.warning("yf.download batch returned empty DataFrame")
            return result

        for sym in symbols:
            try:
                # yfinance returns a MultiIndex (field, ticker) when >1 symbol
                if isinstance(raw.columns, pd.MultiIndex):
                    # Slice this ticker's columns: raw.xs(sym, axis=1, level=1)
                    try:
                        sym_df = raw.xs(sym, axis=1, level=1).copy()
                    except KeyError:
                        # Try stripping exchange suffix  (RELIANCE.NS -> RELIANCE)
                        short = sym.replace(".NS", "")
                        try:
                            sym_df = raw.xs(short, axis=1, level=1).copy()
                        except KeyError:
                            log.warning("batch: symbol %s not found in result", sym)
                            continue
                else:
                    # Single-symbol download (shouldn't happen here but guard)
                    sym_df = raw.copy()

                sym_df = _clean_df(sym_df)
                if _validate_ohlcv(sym_df):
                    result[sym] = sym_df
                else:
                    log.warning("batch: empty/invalid data for %s after clean", sym)
            except Exception as exc:
                log.error("batch: error extracting %s: %s", sym, exc, exc_info=True)

        log.info("yf.download batch: extracted %d/%d symbols", len(result), len(symbols))
    except YFRateLimitError:
        log.warning("yf.download batch rate-limited — will retry symbols individually")
    except Exception as exc:
        log.error("yf.download batch failed: %s", exc, exc_info=True)

    return result


# ---------------------------------------------------------------------------
# Source 1b — yfinance single-symbol (with exponential-backoff retry)
# ---------------------------------------------------------------------------

_yf_last_ok: float = 0.0
_YF_MIN_INTERVAL = 0.3   # seconds between individual fallback fetches
_YF_MAX_RETRIES  = 3


def _yf_history(symbol: str, period: str) -> pd.DataFrame:
    global _yf_last_ok
    elapsed = time.monotonic() - _yf_last_ok
    if elapsed < _YF_MIN_INTERVAL:
        time.sleep(_YF_MIN_INTERVAL - elapsed)

    for attempt in range(_YF_MAX_RETRIES):
        try:
            log.debug("yfinance single fetch: symbol=%s period=%s attempt=%d", symbol, period, attempt + 1)
            df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
            df = _clean_df(df)
            if _validate_ohlcv(df):
                _yf_last_ok = time.monotonic()
                return df
            log.warning("yfinance single: empty/invalid data for %s", symbol)
            return pd.DataFrame()
        except YFRateLimitError:
            wait = 2 ** attempt
            log.warning("yfinance rate-limited: %s attempt=%d — sleeping %ds", symbol, attempt + 1, wait)
            time.sleep(wait)
        except Exception as exc:
            log.error("yfinance single failed: symbol=%s error=%s", symbol, exc, exc_info=True)
            return pd.DataFrame()

    log.error("yfinance single: all retries exhausted for %s", symbol)
    return pd.DataFrame()


def _yf_intraday(symbol: str, period: str = "1d", interval: str = "1m") -> pd.DataFrame:
    global _yf_last_ok
    elapsed = time.monotonic() - _yf_last_ok
    if elapsed < _YF_MIN_INTERVAL:
        time.sleep(_YF_MIN_INTERVAL - elapsed)

    for attempt in range(_YF_MAX_RETRIES):
        try:
            df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
            df = _clean_intraday_df(df)
            if _validate_ohlcv(df):
                _yf_last_ok = time.monotonic()
                return df
            return pd.DataFrame()
        except YFRateLimitError:
            wait = 2 ** attempt
            log.warning("yfinance intraday rate-limited: %s attempt=%d — sleeping %ds", symbol, attempt + 1, wait)
            time.sleep(wait)
        except Exception as exc:
            log.error("yfinance intraday failed: symbol=%s error=%s", symbol, exc, exc_info=True)
            return pd.DataFrame()

    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Source 2 — nselib  (official NSE India REST API)
# ---------------------------------------------------------------------------

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
        end   = datetime.now()
        start = end - timedelta(days=lookback)
        fmt   = "%d-%m-%Y"

        raw = _cm.price_volume_and_deliverable_position_data(
            symbol=ticker,
            from_date=start.strftime(fmt),
            to_date=end.strftime(fmt),
        )
        if raw is None or raw.empty:
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
            return pd.DataFrame()
        raw["Date"] = pd.to_datetime(raw["Date"], dayfirst=True, errors="coerce")
        raw = raw.dropna(subset=["Date"]).set_index("Date").sort_index()

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
    except Exception as exc:
        log.error("nselib fetch failed: symbol=%s period=%s error=%s", symbol, period, exc, exc_info=True)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Staleness guard
# ---------------------------------------------------------------------------

_STALE_STORE: dict[str, pd.DataFrame] = {}


def _warn(msg: str) -> None:
    try:
        if _STREAMLIT_RUNNING:
            existing = st.session_state.get("data_warnings", [])
            if msg not in existing:
                st.session_state["data_warnings"] = existing + [msg]
    except Exception as exc:
        log.debug("_warn() could not write to session_state: %s", exc)


def _fetch_with_fallback(symbol: str, period: str) -> pd.DataFrame:
    """Single-symbol multi-source fetch (used by fetch_ticker and as batch fallback)."""
    key = f"{symbol}:{period}"

    df = _yf_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        return df

    log.warning("yfinance failed for %s/%s — trying nselib", symbol, period)
    df = _nselib_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        _warn(f"🔄 Using NSE backup source for **{symbol}** (Yahoo Finance unavailable)")
        return df

    stale = _STALE_STORE.get(key)
    if stale is not None and not stale.empty:
        log.warning("Serving stale data for %s", symbol)
        _warn(f"⚠️ Serving **stale** data for {symbol} — both live sources failed")
        return stale

    log.error("No data available for %s/%s from any source", symbol, period)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Public cached fetch functions
# ---------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def fetch_ticker(symbol: str, period: str = "3mo") -> pd.DataFrame:
    """Fetch daily OHLCV for one symbol."""
    log.info("fetch_ticker: symbol=%s period=%s", symbol, period)
    return _fetch_with_fallback(symbol, period)


@st.cache_data(ttl=CACHE_TTL)
def fetch_intraday(symbol: str) -> pd.DataFrame:
    """Fetch today's 1-minute bars (market-hours only)."""
    return _yf_intraday(symbol, period="1d", interval="1m")


@st.cache_data(ttl=CACHE_TTL)
def fetch_indices() -> dict[str, pd.DataFrame]:
    """Fetch last-5-day daily bars for all NSE_INDICES."""
    log.info("fetch_indices called")
    symbols = [idx["symbol"] for idx in NSE_INDICES]
    result  = _yf_batch_download(symbols, "5d")
    # Per-symbol fallback for any that missed the batch
    for idx in NSE_INDICES:
        sym = idx["symbol"]
        if sym not in result:
            log.info("fetch_indices: individual fallback for %s", sym)
            df = _fetch_with_fallback(sym, "5d")
            if not df.empty:
                result[sym] = df
    log.info("fetch_indices: loaded %d/%d", len(result), len(NSE_INDICES))
    return result


@st.cache_data(ttl=CACHE_TTL)
def fetch_all_stocks_5d() -> dict[str, pd.DataFrame]:
    """
    Fetch last-5-day daily bars for all 50 Nifty stocks.

    OPTIMISED: Uses yf.download() to fetch all 50 symbols in ONE HTTP
    request (≈2–3 s).  Any symbols missing from the batch result are
    retried individually with nselib / stale-cache fallback.
    """
    log.info("fetch_all_stocks_5d called")
    symbols = [s["symbol"] for s in NIFTY50]

    # --- Step 1: batch download (fast) ---
    result = _yf_batch_download(symbols, "5d")
    log.info("fetch_all_stocks_5d: batch got %d/50 symbols", len(result))

    # --- Step 2: individual fallback for any that failed the batch ---
    missed = [sym for sym in symbols if sym not in result]
    if missed:
        log.warning("fetch_all_stocks_5d: %d symbols missed batch, fetching individually: %s", len(missed), missed)
        for sym in missed:
            df = _fetch_with_fallback(sym, "5d")
            if not df.empty:
                result[sym] = df

    failed = [sym for sym in symbols if sym not in result]
    if failed:
        log.warning("fetch_all_stocks_5d: final missing %d symbols: %s", len(failed), failed)
    log.info("fetch_all_stocks_5d: loaded %d/50 symbols", len(result))
    return result


@st.cache_data(ttl=3600)
def fetch_all_history() -> dict[str, pd.DataFrame]:
    """Fetch 5-year daily bars for all 50 stocks + macro symbols (Time Machine)."""
    log.info("fetch_all_history called (heavy fetch, TTL=3600s)")
    all_syms = SYMBOLS + ["USDINR=X", "CL=F", "GC=F", "^NSEI"]

    # Batch the equity symbols; fetch macro symbols individually
    equity_syms = [s for s in all_syms if not any(c in s for c in ["=", "=X", "=F", "^"])]
    macro_syms  = [s for s in all_syms if s not in equity_syms]

    result = _yf_batch_download(equity_syms, "5y") if equity_syms else {}

    # Individual fallback for missed equities
    for sym in equity_syms:
        if sym not in result:
            df = _fetch_with_fallback(sym, "5y")
            if not df.empty:
                result[sym] = df

    # Macro symbols (USDINR, crude, gold, ^NSEI) fetched individually
    for sym in macro_syms:
        df = _fetch_with_fallback(sym, "5y")
        if not df.empty:
            result[sym] = df

    failed = [s for s in all_syms if s not in result]
    if failed:
        log.warning("fetch_all_history: no data for %d symbols: %s", len(failed), failed)
    log.info("fetch_all_history: loaded %d/%d symbols", len(result), len(all_syms))
    return result


@st.cache_data(ttl=60)
def get_source_status() -> dict[str, str]:
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
