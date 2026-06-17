"""Data fetching helpers with multi-source fallback + SQLite cache.

Priority order for OHLCV history:
  1. SQLite price cache (if data is fresh enough)
  2. yfinance (primary live source)
  3. NSE/BSE unofficial APIs via nsepy / jugaad-trader
  4. Static fallback (last-resort, returns approximate end-of-2024 prices)

Public API
----------
get_stock_data(symbol, period)        → pd.DataFrame (OHLCV)
get_last_price(symbol)                → dict {price, change_pct, day_high, day_low}
get_multiple_stocks(symbols, period)  → dict[str, pd.DataFrame]
"""
from __future__ import annotations

import datetime
import hashlib
import re
import time
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from utils.constants import NIFTY50
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_YF_MAX_RETRIES  = 3
_YF_RETRY_SLEEP  = 1.5      # seconds between yfinance retries
_CACHE_TTL_LIVE  = 120      # seconds — intraday / "1d" period
_CACHE_TTL_HIST  = 3_600    # seconds — multi-day periods
_STALE_THRESHOLD = 0.30     # fraction of missing rows before cache is considered stale

# ---------------------------------------------------------------------------
# Lazy imports (optional heavy deps)
# ---------------------------------------------------------------------------

def _import_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        log.error("yfinance not installed")
        return None


def _import_sqlite():
    try:
        import sqlite3
        return sqlite3
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# SQLite price cache
# ---------------------------------------------------------------------------
_DB_PATH = "price_cache.db"


def _db_conn():
    sq = _import_sqlite()
    if sq is None:
        return None
    try:
        conn = sq.connect(_DB_PATH, check_same_thread=False, timeout=10)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_cache (
                key      TEXT PRIMARY KEY,
                fetched  INTEGER,
                data     BLOB
            )
        """)
        conn.commit()
        return conn
    except Exception as exc:
        log.warning("SQLite open failed: %s", exc)
        return None


def price_cache_read(symbol: str, period: str) -> Optional[pd.DataFrame]:
    conn = _db_conn()
    if conn is None:
        return None
    try:
        key  = f"{symbol}::{period}"
        ttl  = _CACHE_TTL_LIVE if period in ("1d", "2d") else _CACHE_TTL_HIST
        row  = conn.execute(
            "SELECT fetched, data FROM price_cache WHERE key=?", (key,)
        ).fetchone()
        if row is None:
            return None
        fetched, blob = row
        age = time.time() - fetched
        if age > ttl:
            log.debug("cache STALE for %s (age=%.0fs ttl=%ds)", key, age, ttl)
            return None
        df = pd.read_parquet(pd.io.common.BytesIO(blob))
        log.debug("cache HIT %s rows=%d", key, len(df))
        return df
    except Exception as exc:
        log.warning("price_cache_read failed: %s", exc)
        return None
    finally:
        conn.close()


def price_cache_write(symbol: str, period: str, df: pd.DataFrame) -> None:
    conn = _db_conn()
    if conn is None:
        return
    try:
        key = f"{symbol}::{period}"
        buf = pd.io.common.BytesIO()
        df.to_parquet(buf)
        conn.execute(
            "INSERT OR REPLACE INTO price_cache VALUES (?,?,?)",
            (key, int(time.time()), buf.getvalue()),
        )
        conn.commit()
        log.debug("cache WRITE %s rows=%d", key, len(df))
    except Exception as exc:
        log.warning("price_cache_write failed: %s", exc)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DataFrame cleaning & validation
# ---------------------------------------------------------------------------

def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names, drop bad rows, sort by date."""
    if df is None or df.empty:
        return pd.DataFrame()
    # Flatten MultiIndex columns (yfinance sometimes returns them)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    # Ensure standard column names
    rename = {c: c.title().replace(" ", "") for c in df.columns}
    rename.update({"Adj Close": "AdjClose", "Adj_close": "AdjClose"})
    df = df.rename(columns=rename)
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()
    # Drop rows where Close is NaN / zero
    if "Close" in df.columns:
        df = df[pd.to_numeric(df["Close"], errors="coerce").gt(0)]
    return df


def _validate_ohlcv(df: pd.DataFrame, min_rows: int = 2) -> bool:
    if df is None or df.empty or len(df) < min_rows:
        return False
    required = {"Open", "High", "Low", "Close"}
    return required.issubset(df.columns)


# ---------------------------------------------------------------------------
# yfinance single-symbol fetch
# ---------------------------------------------------------------------------

def _yf_history(symbol: str, period: str = "1mo") -> pd.DataFrame:
    yf = _import_yfinance()
    if yf is None:
        return pd.DataFrame()

    # Safety net for symbols with special chars (e.g. M&M.NS).
    # yfinance should handle it, but retry with %26 encoding if it fails.
    _yf_sym = symbol

    for attempt in range(_YF_MAX_RETRIES):
        try:
            log.debug("yfinance single fetch: symbol=%s period=%s attempt=%d", _yf_sym, period, attempt + 1)
            df = yf.Ticker(_yf_sym).history(period=period, auto_adjust=True)
            df = _clean_df(df)
            if _validate_ohlcv(df):
                price_cache_write(symbol, period, df)
                return df
            log.warning("yfinance returned invalid df for %s (attempt %d)", _yf_sym, attempt + 1)
        except Exception as exc:
            # Special case: symbols with & (e.g. M&M.NS) can break URL encoding
            # in some yfinance builds — retry with percent-encoded form once.
            if "&" in _yf_sym and attempt == 0:
                safe_sym = _yf_sym.replace("&", "%26")
                log.warning("yfinance: retrying %s as URL-encoded %s", _yf_sym, safe_sym)
                try:
                    df2 = yf.Ticker(safe_sym).history(period=period, auto_adjust=True)
                    df2 = _clean_df(df2)
                    if _validate_ohlcv(df2):
                        price_cache_write(symbol, period, df2)
                        return df2
                except Exception as enc_exc:
                    log.error("yfinance URL-encoded fallback failed for %s: %s", safe_sym, enc_exc)
            log.error("yfinance single failed: symbol=%s error=%s", symbol, exc, exc_info=True)
            return pd.DataFrame()

        if attempt < _YF_MAX_RETRIES - 1:
            time.sleep(_YF_RETRY_SLEEP)

    log.error("yfinance single: all retries exhausted for %s", symbol)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# yfinance bulk download (faster for many symbols at once)
# ---------------------------------------------------------------------------

def _yf_download_bulk(symbols: list[str], period: str = "1mo") -> dict[str, pd.DataFrame]:
    yf = _import_yfinance()
    if yf is None or not symbols:
        return {}
    try:
        raw = yf.download(
            symbols, period=period, auto_adjust=True,
            progress=False, threads=True, group_by="ticker",
        )
        result: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            try:
                if len(symbols) == 1:
                    df = _clean_df(raw)
                else:
                    df = _clean_df(raw[sym].copy())
                if _validate_ohlcv(df):
                    price_cache_write(sym, period, df)
                    result[sym] = df
            except Exception as sym_exc:
                log.warning("bulk parse failed for %s: %s", sym, sym_exc)
        log.debug("bulk download: got %d/%d symbols", len(result), len(symbols))
        return result
    except Exception as exc:
        log.error("yf.download failed: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=_CACHE_TTL_HIST, show_spinner=False)
def get_stock_data(symbol: str, period: str = "1mo") -> pd.DataFrame:
    """Return OHLCV DataFrame for *symbol* over *period*.

    Falls back through: SQLite cache → yfinance → static data.
    """
    log.info("get_stock_data: symbol=%s period=%s", symbol, period)

    # 1. SQLite cache
    cached = price_cache_read(symbol, period)
    if cached is not None and _validate_ohlcv(cached):
        return cached

    # 2. yfinance
    df = _yf_history(symbol, period)
    if _validate_ohlcv(df):
        return df

    # 3. Static fallback
    log.warning("get_stock_data: all live sources failed for %s, using static data", symbol)
    static = _build_static_hist()
    return static.get(symbol, pd.DataFrame())


@st.cache_data(ttl=_CACHE_TTL_LIVE, show_spinner=False)
def get_last_price(symbol: str) -> dict:
    """Return latest price info dict: {price, change_pct, day_high, day_low}."""
    log.debug("get_last_price: symbol=%s", symbol)
    yf = _import_yfinance()
    if yf is not None:
        try:
            info = yf.Ticker(symbol).fast_info
            price      = float(info.last_price       or 0)
            prev_close = float(info.previous_close   or price)
            day_high   = float(info.day_high         or price)
            day_low    = float(info.day_low          or price)
            change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0
            return {"price": round(price, 2), "change_pct": change_pct,
                    "day_high": round(day_high, 2), "day_low": round(day_low, 2)}
        except Exception as exc:
            log.warning("get_last_price fast_info failed for %s: %s", symbol, exc)
            # fallback: get last row of daily history
            df = get_stock_data(symbol, "2d")
            if not df.empty:
                row = df.iloc[-1]
                close = float(row.get("Close", 0))
                prev  = float(df.iloc[-2].get("Close", close)) if len(df) > 1 else close
                return {
                    "price":      round(close, 2),
                    "change_pct": round((close - prev) / prev * 100, 2) if prev else 0.0,
                    "day_high":   round(float(row.get("High", close)), 2),
                    "day_low":    round(float(row.get("Low",  close)), 2),
                }
    return {"price": 0.0, "change_pct": 0.0, "day_high": 0.0, "day_low": 0.0}


@st.cache_data(ttl=_CACHE_TTL_HIST, show_spinner=False)
def get_multiple_stocks(symbols: tuple[str, ...], period: str = "1mo") -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for multiple symbols, using bulk download where possible."""
    log.info("get_multiple_stocks: %d symbols period=%s", len(symbols), period)
    symbols = list(symbols)

    # Check cache first
    result: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for sym in symbols:
        cached = price_cache_read(sym, period)
        if cached is not None and _validate_ohlcv(cached):
            result[sym] = cached
        else:
            missing.append(sym)

    if missing:
        bulk = _yf_download_bulk(missing, period)
        result.update(bulk)
        # Any still missing → individual fetch
        still_missing = [s for s in missing if s not in result]
        for sym in still_missing:
            df = _yf_history(sym, period)
            if _validate_ohlcv(df):
                result[sym] = df
            else:
                static = _build_static_hist()
                if sym in static:
                    result[sym] = static[sym]

    log.info("get_multiple_stocks: returning %d/%d", len(result), len(symbols))
    return result


# ---------------------------------------------------------------------------
# Nifty 50 universe helper
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def get_nifty50_data(period: str = "1mo") -> dict[str, pd.DataFrame]:
    all_syms = tuple(s["symbol"] for s in NIFTY50)
    return get_multiple_stocks(all_syms, period)


# ---------------------------------------------------------------------------
# Static fallback data builder
# ---------------------------------------------------------------------------

def _build_static_hist() -> dict[str, pd.DataFrame]:
    """Return approximate end-of-2024 price history for all 50 symbols.

    Used only when yfinance is completely unavailable (no internet / cold start).
    Never used for trading signals.
    """
    base_date = datetime.date(2024, 12, 31)
    dates = pd.date_range(end=base_date, periods=30, freq="B")

    static_prices: dict[str, float] = {
        "RELIANCE.NS": 1260,  "TCS.NS": 4100,       "HDFCBANK.NS": 1740,
        "INFY.NS": 1890,      "ICICIBANK.NS": 1280,  "BHARTIARTL.NS": 1580,
        "ITC.NS": 460,        "KOTAKBANK.NS": 1750,  "LT.NS": 3500,
        "HCLTECH.NS": 1820,   "AXISBANK.NS": 1130,   "BAJFINANCE.NS": 6900,
        "WIPRO.NS": 310,      "SUNPHARMA.NS": 1760,  "TITAN.NS": 3300,
        "TATASTEEL.NS": 140,  "MARUTI.NS": 10800,    "NTPC.NS": 345,
        "ONGC.NS": 245,       "POWERGRID.NS": 305,   "ULTRACEMCO.NS": 11500,
        "NESTLEIND.NS": 2250, "ASIANPAINT.NS": 2300, "M&M.NS": 2900,
        "TECHM.NS": 1680,     "BAJAJFINSV.NS": 1720, "TATAMOTORS.NS": 775,
        "ADANIENT.NS": 2400,  "ADANIPORTS.NS": 1180, "SBIN.NS": 815,
        "COALINDIA.NS": 395,  "HINDALCO.NS": 660,    "JSWSTEEL.NS": 930,
        "BPCL.NS": 280,       "CIPLA.NS": 1510,      "DIVISLAB.NS": 5250,
        "DRREDDY.NS": 1270,   "EICHERMOT.NS": 4700,  "GRASIM.NS": 2540,
        "HDFCLIFE.NS": 680,   "HEROMOTOCO.NS": 4300, "INDUSINDBK.NS": 960,
        "LTI.NS": 5200,       "SBILIFE.NS": 1580,    "SHREECEM.NS": 25000,
        "TATACONSUM.NS": 940, "TORNTPHARM.NS": 3100, "UPL.NS": 500,
        "VEDL.NS": 460,       "ZOMATO.NS": 265,
    }

    result: dict[str, pd.DataFrame] = {}
    rng = np.random.default_rng(seed=42)
    for sym in [s["symbol"] for s in NIFTY50]:
        base = static_prices.get(sym, 1000)
        noise = rng.normal(0, base * 0.005, size=30)
        closes = np.maximum(base + np.cumsum(noise), 1.0)
        result[sym] = pd.DataFrame(
            {"Open": closes * 0.998, "High": closes * 1.005,
             "Low":  closes * 0.995, "Close": closes, "Volume": 1_000_000},
            index=dates,
        )
    return result
