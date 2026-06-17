"""
utils/watchlist.py  –  Persistent watchlist storage v2

Storage backends (auto-selected in priority order):
  1. SQLite  (./data/watchlists.db)  – best for self-hosted / Docker
  2. JSON file  (./data/watchlist_{uid}.json)  – lightweight fallback
  3. st.session_state  – last resort for read-only filesystems (Streamlit Cloud)

All public functions are backend-agnostic:
  load_watchlist(user_id)       -> list[str]
  save_watchlist(symbols, uid)  -> None
  add_symbol(symbol, uid)       -> list[str]
  remove_symbol(symbol, uid)    -> list[str]
  get_all_watchlists(uid)       -> dict[str, list[str]]  (named lists)
  create_named_list(name, uid)  -> None
  delete_named_list(name, uid)  -> None
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

_DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DATA_DIR / "watchlists.db"
_DEFAULT_LIST = "Default"


# ─────────────────────────────────────────────────────────────────────────────
# SQLite helpers
# ─────────────────────────────────────────────────────────────────────────────
@contextmanager
def _db():
    conn = sqlite3.connect(_DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_db() -> None:
    with _db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS watchlists (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT    NOT NULL,
                list_name TEXT    NOT NULL DEFAULT 'Default',
                symbol    TEXT    NOT NULL,
                added_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, list_name, symbol)
            );
            CREATE INDEX IF NOT EXISTS idx_user ON watchlists(user_id);
        """)


def _db_available() -> bool:
    try:
        _init_db()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# JSON file helpers (fallback)
# ─────────────────────────────────────────────────────────────────────────────
def _json_path(user_id: str) -> Path:
    safe = "".join(c for c in user_id if c.isalnum() or c in "-_")
    return _DATA_DIR / f"watchlist_{safe}.json"


def _json_load(user_id: str) -> dict[str, list[str]]:
    p = _json_path(user_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {_DEFAULT_LIST: []}


def _json_save(data: dict[str, list[str]], user_id: str) -> None:
    try:
        _json_path(user_id).write_text(json.dumps(data, indent=2))
    except OSError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Session-state helpers (last resort)
# ─────────────────────────────────────────────────────────────────────────────
def _ss_key(user_id: str) -> str:
    return f"__watchlist_{user_id}"


def _ss_load(user_id: str) -> dict[str, list[str]]:
    if _HAS_ST:
        return st.session_state.get(_ss_key(user_id), {_DEFAULT_LIST: []})
    return {_DEFAULT_LIST: []}


def _ss_save(data: dict[str, list[str]], user_id: str) -> None:
    if _HAS_ST:
        st.session_state[_ss_key(user_id)] = data


# ─────────────────────────────────────────────────────────────────────────────
# Unified public API
# ─────────────────────────────────────────────────────────────────────────────
def _use_db() -> bool:
    return _db_available()


def get_all_watchlists(user_id: str = "default") -> dict[str, list[str]]:
    """Returns {list_name: [symbol, ...]} for all named lists of this user."""
    if _use_db():
        with _db() as conn:
            rows = conn.execute(
                "SELECT list_name, symbol FROM watchlists WHERE user_id=? ORDER BY list_name, added_at",
                (user_id,),
            ).fetchall()
        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row["list_name"], []).append(row["symbol"])
        return result or {_DEFAULT_LIST: []}

    data = _json_load(user_id)
    if data:
        return data
    return _ss_load(user_id)


def load_watchlist(user_id: str = "default", list_name: str = _DEFAULT_LIST) -> list[str]:
    """Returns symbols in the specified named list."""
    return get_all_watchlists(user_id).get(list_name, [])


def save_watchlist(
    symbols: list[str],
    user_id: str = "default",
    list_name: str = _DEFAULT_LIST,
) -> None:
    """Replaces all symbols in the specified named list."""
    symbols = sorted(set(s.upper().strip() for s in symbols if s.strip()))
    if _use_db():
        with _db() as conn:
            conn.execute(
                "DELETE FROM watchlists WHERE user_id=? AND list_name=?",
                (user_id, list_name),
            )
            conn.executemany(
                "INSERT OR IGNORE INTO watchlists (user_id, list_name, symbol) VALUES (?,?,?)",
                [(user_id, list_name, s) for s in symbols],
            )
        return

    data = _json_load(user_id)
    data[list_name] = symbols
    _json_save(data, user_id)
    ss = _ss_load(user_id)
    ss[list_name] = symbols
    _ss_save(ss, user_id)


def add_symbol(
    symbol: str,
    user_id: str = "default",
    list_name: str = _DEFAULT_LIST,
) -> list[str]:
    """Adds a symbol; returns updated list."""
    symbol = symbol.upper().strip()
    if _use_db():
        with _db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlists (user_id, list_name, symbol) VALUES (?,?,?)",
                (user_id, list_name, symbol),
            )
        return load_watchlist(user_id, list_name)

    wl = load_watchlist(user_id, list_name)
    if symbol not in wl:
        wl.append(symbol)
        save_watchlist(wl, user_id, list_name)
    return wl


def remove_symbol(
    symbol: str,
    user_id: str = "default",
    list_name: str = _DEFAULT_LIST,
) -> list[str]:
    """Removes a symbol; returns updated list."""
    symbol = symbol.upper().strip()
    if _use_db():
        with _db() as conn:
            conn.execute(
                "DELETE FROM watchlists WHERE user_id=? AND list_name=? AND symbol=?",
                (user_id, list_name, symbol),
            )
        return load_watchlist(user_id, list_name)

    wl = [s for s in load_watchlist(user_id, list_name) if s != symbol]
    save_watchlist(wl, user_id, list_name)
    return wl


def create_named_list(list_name: str, user_id: str = "default") -> None:
    """Creates an empty named watchlist (no-op if already exists)."""
    if not load_watchlist(user_id, list_name):
        save_watchlist([], user_id, list_name)


def delete_named_list(list_name: str, user_id: str = "default") -> None:
    """Deletes a named watchlist entirely."""
    if list_name == _DEFAULT_LIST:
        return   # protect default list
    if _use_db():
        with _db() as conn:
            conn.execute(
                "DELETE FROM watchlists WHERE user_id=? AND list_name=?",
                (user_id, list_name),
            )
        return
    data = _json_load(user_id)
    data.pop(list_name, None)
    _json_save(data, user_id)
