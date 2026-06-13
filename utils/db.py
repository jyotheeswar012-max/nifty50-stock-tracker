"""
utils/db.py  —  Supabase DB helpers with safe session-state fallbacks.
If Supabase is not configured every function falls back to st.session_state
so the app never crashes.
"""
from __future__ import annotations
import streamlit as st
from typing import Any


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
