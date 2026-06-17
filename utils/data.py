"""Data fetching helpers with multi-source fallback + SQLite price cache.

Fetch waterfall
---------------
0. SQLite cache  (utils/db.price_cache_read)  — fastest, survives rate limits
1. yfinance batch  (yf.download all 50 at once)
2. yfinance single (per-symbol fallback for any that failed the batch)
3. nselib           — official NSE India REST API, no auth required
4. SQLite stale    (price_cache_read_stale)   — last resort, any age accepted

Every successful live fetch is written through to the SQLite cache
(price_cache_write) so Layer 0 is always warm after the first run.

Dynamic beta computation
------------------------
After fetch_all_history() assembles its result dict, compute_betas()
calculates a 1-year rolling OLS beta for every equity symbol against
^NSEI daily returns.  The results are stored in
  st.session_state["dynamic_betas"]  →  {"RELIANCE.NS": 0.92, ...}
and consumed by calculations.py / app.py instead of the static
constants.NIFTY50[i]["beta"] values.  Constants betas remain as
a cold-start fallback when history data is not yet loaded.

All @st.cache_data decorators live here so caching is co-located with
the fetch logic.  app.py imports only the cached public functions.

Importability note
------------------
When this module is imported outside a running Streamlit server (e.g.
during pytest), `@st.cache_data` is replaced with a transparent no-op
decorator so all public functions remain fully testable without a live
Streamlit context.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Callable

import numpy as np
import pandas as pd
import pytz
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from utils.constants import CACHE_TTL, NIFTY50, NSE_INDICES, SYMBOLS
from utils.logger import get_logger
from utils.db import (
    price_cache_read,
    price_cache_read_stale,
    price_cache_write,
    price_cache_purge_old,
)

log = get_logger(__name__)   # nse_tracker.utils.data

# Evict DB rows older than 7 days on first import (lazy housekeeping)
try:
    price_cache_purge_old(max_age_days=7)
except Exception:
    pass

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
            def __setitem__(cls, key, value):
                cls._store[key] = value
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
# Source 0 — SQLite cache read (fastest, survives rate limits)
# ---------------------------------------------------------------------------

# TTL for considering a SQLite-cached row "fresh" enough to skip live fetch.
# Intentionally slightly longer than CACHE_TTL so a single Streamlit cache
# expiry doesn't force a redundant network call if the DB row is recent.
_SQLITE_FRESH_TTL = max(CACHE_TTL * 2, 60)   # seconds


# ---------------------------------------------------------------------------
# Source 1a — yfinance BATCH download  (all symbols in ONE HTTP request)
# ---------------------------------------------------------------------------

def _yf_batch_download(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV for all symbols in a single yf.download() call.
    Returns a dict {symbol: DataFrame}.  Symbols that come back empty
    are omitted so the caller can fall back individually.
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
            group_by="ticker",
            progress=False,
            threads=True,
            timeout=30,
        )
        elapsed = time.monotonic() - t0
        log.info("yf.download batch finished in %.1fs", elapsed)

        if raw.empty:
            log.warning("yf.download batch returned empty DataFrame")
            return result

        for sym in symbols:
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    try:
                        sym_df = raw.xs(sym, axis=1, level=1).copy()
                    except KeyError:
                        short = sym.replace(".NS", "")
                        try:
                            sym_df = raw.xs(short, axis=1, level=1).copy()
                        except KeyError:
                            log.warning("batch: symbol %s not found in result", sym)
                            continue
                else:
                    sym_df = raw.copy()

                sym_df = _clean_df(sym_df)
                if _validate_ohlcv(sym_df):
                    result[sym] = sym_df
                    price_cache_write(sym, period, sym_df)  # write-through
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
                price_cache_write(symbol, period, df)  # write-through
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
            price_cache_write(symbol, period, df)  # write-through
            return df
    except Exception as exc:
        log.error("nselib fetch failed: symbol=%s period=%s error=%s", symbol, period, exc, exc_info=True)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Staleness guard (in-memory, kept for intra-process resilience)
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
    """
    Full fetch waterfall for a single symbol:
      0. SQLite (fresh)  →  1. yfinance single  →  2. nselib
      →  3. SQLite (stale)  →  4. in-memory stale store
    """
    key = f"{symbol}:{period}"

    # --- Layer 0: SQLite fresh cache ---
    cached = price_cache_read(symbol, period, max_age_s=_SQLITE_FRESH_TTL)
    if not cached.empty:
        log.debug("_fetch_with_fallback: SQLite cache hit for %s/%s", symbol, period)
        _STALE_STORE[key] = cached   # keep in-memory store warm too
        return cached

    # --- Layer 1: yfinance single ---
    df = _yf_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        return df   # write-through already done inside _yf_history

    # --- Layer 2: nselib ---
    log.warning("yfinance failed for %s/%s — trying nselib", symbol, period)
    df = _nselib_history(symbol, period)
    if not df.empty:
        _STALE_STORE[key] = df
        _warn(f"\U0001f504 Using NSE backup source for **{symbol}** (Yahoo Finance unavailable)")
        return df   # write-through already done inside _nselib_history

    # --- Layer 3: SQLite stale (any age) ---
    stale_db = price_cache_read_stale(symbol, period)
    if not stale_db.empty:
        log.warning("Serving SQLite stale data for %s", symbol)
        _warn(f"\u26a0\ufe0f Serving **stale cached** data for {symbol} — all live sources failed")
        _STALE_STORE[key] = stale_db
        return stale_db

    # --- Layer 4: in-memory stale ---
    stale_mem = _STALE_STORE.get(key)
    if stale_mem is not None and not stale_mem.empty:
        log.warning("Serving in-memory stale data for %s", symbol)
        _warn(f"\u26a0\ufe0f Serving **stale** data for {symbol} — both live sources failed")
        return stale_mem

    log.error("No data available for %s/%s from any source", symbol, period)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Dynamic beta computation
# ---------------------------------------------------------------------------

# Minimum number of overlapping daily-return observations to compute beta.
_BETA_MIN_OBS = 60   # ~3 months of trading days


def compute_betas(
    history: dict[str, pd.DataFrame],
    lookback_days: int = 252,
) -> dict[str, float]:
    """
    Compute 1-year OLS beta for every equity symbol in *history* against
    the Nifty 50 index (^NSEI).

    Beta = Cov(r_stock, r_index) / Var(r_index)

    Parameters
    ----------
    history        : dict returned by fetch_all_history()
    lookback_days  : number of most-recent trading days to use (default 252 = 1y)

    Returns
    -------
    dict mapping symbol → float beta.  Symbols with insufficient data
    are omitted; callers should fall back to constants.NIFTY50 beta.
    """
    betas: dict[str, float] = {}

    nsei_df = history.get("^NSEI")
    if nsei_df is None or nsei_df.empty:
        log.warning("compute_betas: ^NSEI not in history, skipping dynamic beta")
        return betas

    nsei_close = _to_series(nsei_df["Close"]).dropna().astype(float)
    nsei_ret   = nsei_close.pct_change().dropna()

    # Restrict to the most-recent window
    if len(nsei_ret) > lookback_days:
        nsei_ret = nsei_ret.iloc[-lookback_days:]

    for sym in SYMBOLS:
        try:
            sym_df = history.get(sym)
            if sym_df is None or sym_df.empty:
                continue

            sym_close = _to_series(sym_df["Close"]).dropna().astype(float)
            sym_ret   = sym_close.pct_change().dropna()

            # Align on common dates
            common_idx  = nsei_ret.index.intersection(sym_ret.index)
            if len(common_idx) < _BETA_MIN_OBS:
                log.debug(
                    "compute_betas: %s has only %d common obs (need %d) — skipping",
                    sym, len(common_idx), _BETA_MIN_OBS,
                )
                continue

            r_mkt  = nsei_ret.loc[common_idx].values.astype(float)
            r_stk  = sym_ret.loc[common_idx].values.astype(float)

            var_mkt = np.var(r_mkt, ddof=1)
            if var_mkt == 0 or np.isnan(var_mkt):
                continue

            beta = float(np.cov(r_stk, r_mkt, ddof=1)[0, 1] / var_mkt)

            # Sanity clamp: beta outside [-2, 4] almost certainly means bad data
            if not (-2.0 <= beta <= 4.0):
                log.warning("compute_betas: %s beta=%.3f out of range, clamping", sym, beta)
                beta = float(np.clip(beta, -2.0, 4.0))

            betas[sym] = round(beta, 4)
        except Exception as exc:
            log.error("compute_betas: error for %s: %s", sym, exc, exc_info=True)

    log.info(
        "compute_betas: computed %d/%d betas (lookback=%d days)",
        len(betas), len(SYMBOLS), lookback_days,
    )
    return betas


def get_beta(symbol: str) -> float:
    """
    Return the best available beta for *symbol*.

    Priority:
      1. st.session_state["dynamic_betas"]  (live-computed)
      2. constants.NIFTY50 static beta       (cold-start fallback)
      3. 1.0                                 (market-neutral default)
    """
    try:
        dynamic = st.session_state.get("dynamic_betas", {})
        if symbol in dynamic:
            return dynamic[symbol]
    except Exception:
        pass

    # Fallback: static constants
    for s in NIFTY50:
        if s["symbol"] == symbol:
            return s.get("beta", 1.0)
    return 1.0


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
    request (~2-3 s).  Any symbols missing from the batch result are
    retried individually with nselib / SQLite / stale-cache fallback.
    """
    log.info("fetch_all_stocks_5d called")
    symbols = [s["symbol"] for s in NIFTY50]

    # Step 1: batch download (fast)
    result = _yf_batch_download(symbols, "5d")
    log.info("fetch_all_stocks_5d: batch got %d/50 symbols", len(result))

    # Step 2: individual fallback for any that failed the batch
    missed = [sym for sym in symbols if sym not in result]
    if missed:
        log.warning(
            "fetch_all_stocks_5d: %d symbols missed batch, fetching individually: %s",
            len(missed), missed,
        )
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
    """
    Fetch 5-year daily bars for all 50 stocks + macro symbols (Time Machine).

    After assembling the result dict, dynamically computes OLS betas
    against ^NSEI and stores them in st.session_state["dynamic_betas"]
    so all other pages pick them up via get_beta().
    """
    log.info("fetch_all_history called (heavy fetch, TTL=3600s)")
    all_syms = SYMBOLS + ["USDINR=X", "CL=F", "GC=F", "^NSEI"]

    equity_syms = [s for s in all_syms if not any(c in s for c in ["=", "=X", "=F", "^"])]
    macro_syms  = [s for s in all_syms if s not in equity_syms]

    result = _yf_batch_download(equity_syms, "5y") if equity_syms else {}

    # Individual fallback for missed equities
    for sym in equity_syms:
        if sym not in result:
            df = _fetch_with_fallback(sym, "5y")
            if not df.empty:
                result[sym] = df

    # Macro symbols fetched individually
    for sym in macro_syms:
        df = _fetch_with_fallback(sym, "5y")
        if not df.empty:
            result[sym] = df

    failed = [s for s in all_syms if s not in result]
    if failed:
        log.warning("fetch_all_history: no data for %d symbols: %s", len(failed), failed)
    log.info("fetch_all_history: loaded %d/%d symbols", len(result), len(all_syms))

    # --- Compute dynamic betas and publish to session_state ---
    try:
        dynamic_betas = compute_betas(result, lookback_days=252)
        if dynamic_betas:
            st.session_state["dynamic_betas"] = dynamic_betas
            log.info(
                "fetch_all_history: stored %d dynamic betas in session_state",
                len(dynamic_betas),
            )
        else:
            log.warning("fetch_all_history: compute_betas returned empty dict — keeping static betas")
    except Exception as exc:
        log.error("fetch_all_history: compute_betas failed: %s", exc, exc_info=True)

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

    # SQLite cache health
    try:
        from utils.db import _db_conn
        conn = _db_conn()
        if conn:
            conn.execute("SELECT COUNT(*) FROM price_cache").fetchone()
            conn.close()
            status["sqlite_cache"] = "ok"
        else:
            status["sqlite_cache"] = "unavailable"
    except Exception:
        status["sqlite_cache"] = "error"

    log.info("get_source_status result: %s", status)
    return status
