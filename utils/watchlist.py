"""
utils/watchlist.py  —  SQLite-backed user watchlist persistence.

Schema
------
  watchlists   (id INTEGER PK, user_id TEXT, name TEXT, created_at REAL,
                UNIQUE(user_id, name))
  watchlist_items (id INTEGER PK, watchlist_id INTEGER FK, symbol TEXT,
                   position INTEGER, added_at REAL,
                   UNIQUE(watchlist_id, symbol))

All writes are transactional.  Positions are dense integers starting at 0;
reorder() rebuilds them atomically.

Public API
----------
  list_watchlists(user_id)              -> list[dict]
  create_watchlist(user_id, name)       -> int  (new watchlist id)
  rename_watchlist(wl_id, new_name)     -> None
  delete_watchlist(wl_id)               -> None

  get_symbols(wl_id)                    -> list[str]
  add_symbol(wl_id, symbol)             -> None
  remove_symbol(wl_id, symbol)          -> None
  reorder_symbols(wl_id, ordered_syms)  -> None

  export_csv(wl_id)                     -> str  (CSV text)
"""
from __future__ import annotations

import csv
import io
import time
from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# DB bootstrap
# ---------------------------------------------------------------------------

def _conn():
    """Return a connection to the shared SQLite database."""
    from utils.db import _db_conn
    return _db_conn()


def _ensure_schema() -> None:
    """Create tables if they don't exist (idempotent)."""
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlists (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT    NOT NULL,
            name        TEXT    NOT NULL,
            created_at  REAL    NOT NULL DEFAULT (unixepoch()),
            UNIQUE(user_id, name)
        );
        CREATE TABLE IF NOT EXISTS watchlist_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
            symbol       TEXT    NOT NULL,
            position     INTEGER NOT NULL DEFAULT 0,
            added_at     REAL    NOT NULL DEFAULT (unixepoch()),
            UNIQUE(watchlist_id, symbol)
        );
        CREATE INDEX IF NOT EXISTS idx_wl_user   ON watchlists(user_id);
        CREATE INDEX IF NOT EXISTS idx_wli_wl    ON watchlist_items(watchlist_id);
    """)
    conn.commit()
    conn.close()


_ensure_schema()


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------

def list_watchlists(user_id: str) -> list[dict[str, Any]]:
    """Return all watchlists owned by *user_id*, ordered by creation time."""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, name, created_at FROM watchlists WHERE user_id=? ORDER BY created_at",
        (user_id,),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]


def create_watchlist(user_id: str, name: str) -> int:
    """Create a new watchlist.  Returns the new watchlist id."""
    name = name.strip()
    if not name:
        raise ValueError("Watchlist name cannot be empty")
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO watchlists (user_id, name, created_at) VALUES (?,?,?)",
            (user_id, name, time.time()),
        )
        conn.commit()
        new_id = cur.lastrowid
        log.info("create_watchlist: user=%s name=%r id=%d", user_id, name, new_id)
        return new_id
    except Exception as exc:
        conn.rollback()
        raise
    finally:
        conn.close()


def rename_watchlist(wl_id: int, new_name: str) -> None:
    """Rename watchlist *wl_id* to *new_name*."""
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Watchlist name cannot be empty")
    conn = _conn()
    try:
        conn.execute("UPDATE watchlists SET name=? WHERE id=?", (new_name, wl_id))
        conn.commit()
        log.info("rename_watchlist: id=%d new_name=%r", wl_id, new_name)
    finally:
        conn.close()


def delete_watchlist(wl_id: int) -> None:
    """Delete watchlist and all its items (CASCADE)."""
    conn = _conn()
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM watchlists WHERE id=?", (wl_id,))
        conn.commit()
        log.info("delete_watchlist: id=%d", wl_id)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Symbol CRUD
# ---------------------------------------------------------------------------

def get_symbols(wl_id: int) -> list[str]:
    """Return ordered symbol list for watchlist *wl_id*."""
    conn = _conn()
    rows = conn.execute(
        "SELECT symbol FROM watchlist_items WHERE watchlist_id=? ORDER BY position, added_at",
        (wl_id,),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def add_symbol(wl_id: int, symbol: str) -> None:
    """Append *symbol* to watchlist *wl_id* (no-op if already present)."""
    symbol = symbol.strip().upper()
    conn = _conn()
    try:
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM watchlist_items WHERE watchlist_id=?",
            (wl_id,),
        ).fetchone()[0]
        conn.execute(
            """
            INSERT OR IGNORE INTO watchlist_items (watchlist_id, symbol, position, added_at)
            VALUES (?,?,?,?)
            """,
            (wl_id, symbol, max_pos + 1, time.time()),
        )
        conn.commit()
        log.debug("add_symbol: wl_id=%d symbol=%s", wl_id, symbol)
    finally:
        conn.close()


def remove_symbol(wl_id: int, symbol: str) -> None:
    """Remove *symbol* from watchlist *wl_id*."""
    symbol = symbol.strip().upper()
    conn = _conn()
    try:
        conn.execute(
            "DELETE FROM watchlist_items WHERE watchlist_id=? AND symbol=?",
            (wl_id, symbol),
        )
        conn.commit()
        log.debug("remove_symbol: wl_id=%d symbol=%s", wl_id, symbol)
    finally:
        conn.close()


def reorder_symbols(wl_id: int, ordered_syms: list[str]) -> None:
    """
    Reassign dense positions [0, 1, 2, …] to *ordered_syms* atomically.
    Symbols not present in *ordered_syms* are left at the end.
    """
    conn = _conn()
    try:
        existing = [r[0] for r in conn.execute(
            "SELECT symbol FROM watchlist_items WHERE watchlist_id=? ORDER BY position",
            (wl_id,),
        ).fetchall()]
        # Build full ordered list: requested order first, then any stragglers
        ordered = list(ordered_syms) + [s for s in existing if s not in ordered_syms]
        for pos, sym in enumerate(ordered):
            conn.execute(
                "UPDATE watchlist_items SET position=? WHERE watchlist_id=? AND symbol=?",
                (pos, wl_id, sym),
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(wl_id: int) -> str:
    """Return a CSV string of all symbols in watchlist *wl_id*."""
    conn = _conn()
    rows = conn.execute(
        """
        SELECT w.name, i.symbol, i.position, datetime(i.added_at, 'unixepoch') as added_at
        FROM watchlist_items i
        JOIN watchlists w ON w.id = i.watchlist_id
        WHERE i.watchlist_id=?
        ORDER BY i.position
        """,
        (wl_id,),
    ).fetchall()
    conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["watchlist", "symbol", "position", "added_at"])
    writer.writerows(rows)
    return buf.getvalue()
