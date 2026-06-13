"""
utils/db.py

Supabase DB helpers for persistent user data.
Tables (create once via SQL editor in Supabase dashboard):

-- WATCHLIST
create table if not exists watchlist (
  id           uuid default gen_random_uuid() primary key,
  user_id      uuid references auth.users(id) on delete cascade,
  stock_name   text not null,
  symbol       text not null,
  created_at   timestamptz default now()
);
alter table watchlist enable row level security;
create policy "own watchlist" on watchlist for all using (auth.uid() = user_id);

-- ALERTS
create table if not exists alerts (
  id           uuid default gen_random_uuid() primary key,
  user_id      uuid references auth.users(id) on delete cascade,
  stock_name   text not null,
  symbol       text not null,
  direction    text not null,
  threshold    float not null,
  active       boolean default true,
  created_at   timestamptz default now()
);
alter table alerts enable row level security;
create policy "own alerts" on alerts for all using (auth.uid() = user_id);
"""
from __future__ import annotations
import streamlit as st
from typing import Optional


def _client():
    try:
        from supabase import create_client
        cfg = st.secrets["supabase"]
        return create_client(str(cfg["url"]), str(cfg["anon_key"]))
    except Exception:
        return None


def _uid() -> Optional[str]:
    user = st.session_state.get("sb_user")
    return user["id"] if user else None


# ──────────────────────────── WATCHLIST ────────────────────────────

def wl_load() -> list[dict]:
    """Load watchlist from Supabase for current user."""
    client = _client()
    uid = _uid()
    if not client or not uid:
        return st.session_state.get("watchlist_local", [])
    try:
        res = client.table("watchlist").select("*").eq("user_id", uid).order("created_at").execute()
        return res.data or []
    except Exception:
        return st.session_state.get("watchlist_local", [])


def wl_add(stock_name: str, symbol: str) -> bool:
    client = _client()
    uid = _uid()
    if not client or not uid:
        # fallback session
        local = st.session_state.setdefault("watchlist_local", [])
        if not any(w["stock_name"] == stock_name for w in local):
            local.append({"stock_name": stock_name, "symbol": symbol})
        return True
    try:
        client.table("watchlist").insert({"user_id": uid, "stock_name": stock_name, "symbol": symbol}).execute()
        return True
    except Exception:
        return False


def wl_remove(stock_name: str) -> bool:
    client = _client()
    uid = _uid()
    if not client or not uid:
        local = st.session_state.get("watchlist_local", [])
        st.session_state["watchlist_local"] = [w for w in local if w["stock_name"] != stock_name]
        return True
    try:
        client.table("watchlist").delete().eq("user_id", uid).eq("stock_name", stock_name).execute()
        return True
    except Exception:
        return False


# ──────────────────────────── ALERTS ───────────────────────────────

def al_load() -> list[dict]:
    client = _client()
    uid = _uid()
    if not client or not uid:
        return st.session_state.get("alerts", [])
    try:
        res = client.table("alerts").select("*").eq("user_id", uid).eq("active", True).order("created_at").execute()
        rows = res.data or []
        # normalise to match session format
        return [
            {
                "db_id":     r["id"],
                "stock":     r["stock_name"],
                "symbol":    r["symbol"],
                "direction": r["direction"],
                "threshold": float(r["threshold"]),
                "added":     r["created_at"][:19].replace("T", " "),
            }
            for r in rows
        ]
    except Exception:
        return st.session_state.get("alerts", [])


def al_add(stock_name: str, symbol: str, direction: str, threshold: float) -> bool:
    client = _client()
    uid = _uid()
    if not client or not uid:
        st.session_state.setdefault("alerts", []).append({
            "stock": stock_name, "symbol": symbol,
            "direction": direction, "threshold": threshold, "added": "session",
        })
        return True
    try:
        client.table("alerts").insert({
            "user_id": uid, "stock_name": stock_name, "symbol": symbol,
            "direction": direction, "threshold": threshold,
        }).execute()
        return True
    except Exception:
        return False


def al_delete(alert: dict) -> bool:
    client = _client()
    uid = _uid()
    db_id = alert.get("db_id")
    if not client or not uid or not db_id:
        return False
    try:
        client.table("alerts").update({"active": False}).eq("id", db_id).execute()
        return True
    except Exception:
        return False


def al_clear() -> bool:
    client = _client()
    uid = _uid()
    if not client or not uid:
        st.session_state["alerts"] = []
        return True
    try:
        client.table("alerts").update({"active": False}).eq("user_id", uid).execute()
        return True
    except Exception:
        return False
