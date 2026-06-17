"""
utils/db.py  —  Supabase DB helpers with safe session-state fallbacks,
                PLUS a local SQLite price-cache layer for yfinance resilience.

SQLite price cache
------------------
The cache stores the most-recent successful OHLCV fetch for every
(symbol, period) pair as a compressed Parquet blob.  It is used in
data.py as Layer 0 in the fetch waterfall:

    SQLite (fresh?) → yfinance batch → yfinance single → nselib → SQLite (stale)

The DB file lives at ~/.cache/nse_tracker/price_cache.db so it
persists across Streamlit hot-reloads.  Each row carries a
`fetched_at` UTC timestamp; callers decide freshness via the
`max_age_s` argument (default: 900 s = 15 min).

No new pip dependency is required — sqlite3 and io are in the stdlib;
pyarrow is already present (required by Streamlit/pandas).

Supabase helpers
----------------
All existing alert / watchlist helpers are unchanged.
"""
from __future__ import annotations

import io
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger("nse_tracker.utils.db")

# ---------------------------------------------------------------------------
# SQLite setup
# ---------------------------------------------------------------------------

_CACHE_DIR  = Path(os.environ.get("NSE_CACHE_DIR", Path.home() / ".cache" / "nse_tracker"))
_DB_PATH    = _CACHE_DIR / "price_cache.db"
_TABLE_DDL  = """
CREATE TABLE IF NOT EXISTS price_cache (
    symbol      TEXT    NOT NULL,
    period      TEXT    NOT NULL,
    fetched_at  REAL    NOT NULL,   -- Unix timestamp (UTC)
    parquet     BLOB    NOT NULL,   -- gzip-compressed Parquet bytes
    PRIMARY KEY (symbol, period)
);
CREATE INDEX IF NOT EXISTS idx_pc_symbol ON price_cache (symbol);
"""


def _db_conn() -> sqlite3.Connection | None:
    """Return a thread-local SQLite connection, creating the DB file if needed."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.executescript(_TABLE_DDL)
        conn.commit()
        return conn
    except Exception as exc:
        log.warning("SQLite price cache unavailable: %s", exc)
        return None


def _df_to_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, engine="pyarrow", compression="gzip")
    return buf.getvalue()


def _bytes_to_df(blob: bytes) -> pd.DataFrame:
    return pd.read_parquet(io.BytesIO(blob), engine="pyarrow")


# ---------------------------------------------------------------------------
# Public price-cache API  (used by utils/data.py)
# ---------------------------------------------------------------------------

def price_cache_read(
    symbol: str,
    period: str,
    max_age_s: float = 900.0,
) -> pd.DataFrame:
    """
    Return the cached DataFrame for (symbol, period) if it exists and is
    younger than *max_age_s* seconds.  Returns an empty DataFrame otherwise.

    Pass ``max_age_s=float('inf')`` to read stale data unconditionally
    (used as last-resort fallback when all live sources fail).
    """
    conn = _db_conn()
    if conn is None:
        return pd.DataFrame()
    try:
        cur = conn.execute(
            "SELECT fetched_at, parquet FROM price_cache WHERE symbol=? AND period=?",
            (symbol, period),
        )
        row = cur.fetchone()
        if row is None:
            return pd.DataFrame()
        fetched_at, blob = row
        age = time.time() - fetched_at
        if age > max_age_s:
            log.debug("price_cache: stale (%.0fs) for %s/%s", age, symbol, period)
            return pd.DataFrame()   # caller should treat as miss
        df = _bytes_to_df(blob)
        log.debug("price_cache HIT: %s/%s age=%.0fs rows=%d", symbol, period, age, len(df))
        return df
    except Exception as exc:
        log.warning("price_cache_read error for %s/%s: %s", symbol, period, exc)
        return pd.DataFrame()
    finally:
        conn.close()


def price_cache_write(symbol: str, period: str, df: pd.DataFrame) -> None:
    """
    Upsert *df* into the local price cache.  Silently swallows errors so a
    write failure never propagates to the UI.
    """
    if df is None or df.empty:
        return
    conn = _db_conn()
    if conn is None:
        return
    try:
        blob = _df_to_bytes(df)
        conn.execute(
            """
            INSERT INTO price_cache (symbol, period, fetched_at, parquet)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol, period)
            DO UPDATE SET fetched_at=excluded.fetched_at,
                          parquet=excluded.parquet
            """,
            (symbol, period, time.time(), blob),
        )
        conn.commit()
        log.debug("price_cache WRITE: %s/%s rows=%d", symbol, period, len(df))
    except Exception as exc:
        log.warning("price_cache_write error for %s/%s: %s", symbol, period, exc)
    finally:
        conn.close()


def price_cache_read_stale(symbol: str, period: str) -> pd.DataFrame:
    """Read cached data regardless of age (last-resort fallback)."""
    return price_cache_read(symbol, period, max_age_s=float("inf"))


def price_cache_evict(symbol: str, period: str) -> None:
    """Remove a specific cache entry (useful after a confirmed bad write)."""
    conn = _db_conn()
    if conn is None:
        return
    try:
        conn.execute("DELETE FROM price_cache WHERE symbol=? AND period=?", (symbol, period))
        conn.commit()
    except Exception as exc:
        log.warning("price_cache_evict error: %s", exc)
    finally:
        conn.close()


def price_cache_purge_old(max_age_days: int = 7) -> int:
    """
    Delete rows older than *max_age_days*.  Called lazily on first load
    to prevent unbounded DB growth.  Returns number of rows deleted.
    """
    conn = _db_conn()
    if conn is None:
        return 0
    try:
        cutoff = time.time() - max_age_days * 86_400
        cur = conn.execute("DELETE FROM price_cache WHERE fetched_at < ?", (cutoff,))
        conn.commit()
        n = cur.rowcount
        if n:
            log.info("price_cache_purge_old: removed %d rows older than %d days", n, max_age_days)
        return n
    except Exception as exc:
        log.warning("price_cache_purge_old error: %s", exc)
        return 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Supabase client helpers (unchanged)
# ---------------------------------------------------------------------------

import streamlit as st  # noqa: E402  (must follow stdlib imports)


def _client():
    try:
        from utils.supabase_auth import _get_client
        return _get_client()
    except Exception:
        return None


def _uid() -> str | None:
    try:
        u = st.session_state.get("sb_user")
        return u["id"] if u else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────── ALERTS

def al_load() -> list[dict]:
    client = _client(); uid = _uid()
    if client and uid:
        try:
            res = client.table("alerts").select("*").eq("user_id", uid).execute()
            return res.data or []
        except Exception:
            pass
    return st.session_state.get("alerts", [])


def al_add(stock_name: str, symbol: str, direction: str, threshold: float) -> bool:
    client = _client(); uid = _uid()
    if client and uid:
        try:
            client.table("alerts").insert({
                "user_id": uid, "stock_name": stock_name,
                "symbol": symbol, "direction": direction,
                "threshold": threshold,
            }).execute()
            return True
        except Exception:
            pass
    st.session_state.setdefault("alerts", []).append({
        "stock_name": stock_name, "symbol": symbol,
        "direction": direction, "threshold": threshold,
        "added": "session", "db_id": None,
    })
    return True


def al_delete(alert: dict) -> bool:
    client = _client()
    if client and alert.get("id"):
        try:
            client.table("alerts").delete().eq("id", alert["id"]).execute()
            return True
        except Exception:
            pass
    st.session_state["alerts"] = [
        a for a in st.session_state.get("alerts", []) if a != alert
    ]
    return True


def al_clear() -> bool:
    client = _client(); uid = _uid()
    if client and uid:
        try:
            client.table("alerts").delete().eq("user_id", uid).execute()
            st.session_state["alerts"] = []
            return True
        except Exception:
            pass
    st.session_state["alerts"] = []
    return True


# ───────────────────────────────────────────────────────────── WATCHLIST

def wl_load() -> list[str]:
    client = _client(); uid = _uid()
    if client and uid:
        try:
            res = client.table("watchlist").select("stock_name").eq("user_id", uid).execute()
            return [r["stock_name"] for r in (res.data or [])]
        except Exception:
            pass
    return st.session_state.get("watchlist", [])


def wl_add(stock_name: str) -> bool:
    client = _client(); uid = _uid()
    existing = wl_load()
    if stock_name in existing:
        return True
    if client and uid:
        try:
            client.table("watchlist").insert({"user_id": uid, "stock_name": stock_name}).execute()
            return True
        except Exception:
            pass
    wl = st.session_state.get("watchlist", [])
    if stock_name not in wl:
        wl.append(stock_name)
    st.session_state["watchlist"] = wl
    return True


def wl_remove(stock_name: str) -> bool:
    client = _client(); uid = _uid()
    if client and uid:
        try:
            client.table("watchlist").delete().eq("user_id", uid).eq("stock_name", stock_name).execute()
            return True
        except Exception:
            pass
    st.session_state["watchlist"] = [
        s for s in st.session_state.get("watchlist", []) if s != stock_name
    ]
    return True
