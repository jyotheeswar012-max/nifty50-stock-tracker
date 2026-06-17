"""
pages/9_Watchlists.py  —  Persistent watchlist manager.

Features
--------
  • Create / rename / delete named watchlists
  • Add / remove symbols from any Nifty 50 list
  • Drag-sort via up/down buttons (SQLite positions updated atomically)
  • Export watchlist as CSV
  • Per-user namespacing via Streamlit session_state user_id
    (falls back to "guest" when auth is not active)
"""
from __future__ import annotations

import streamlit as st

from utils.constants import NIFTY50, SYMBOLS
from utils.watchlist import (
    add_symbol,
    create_watchlist,
    delete_watchlist,
    export_csv,
    get_symbols,
    list_watchlists,
    remove_symbol,
    rename_watchlist,
    reorder_symbols,
)

st.set_page_config(page_title="Watchlists", page_icon="❤️", layout="wide")
st.title("❤️ Watchlists")
st.caption("Create named watchlists, add/remove symbols, and export them as CSV.")

# ---------------------------------------------------------------------------
# Resolve user id
# ---------------------------------------------------------------------------
user_id: str = st.session_state.get("user_id") or "guest"

# ---------------------------------------------------------------------------
# Watchlist selector / creator
# ---------------------------------------------------------------------------
watchlists = list_watchlists(user_id)

col_sel, col_new = st.columns([3, 2])

with col_new:
    with st.form("new_wl_form", clear_on_submit=True):
        new_name = st.text_input("New watchlist name", placeholder="e.g. My Pharma Picks")
        if st.form_submit_button("➕ Create") and new_name.strip():
            try:
                create_watchlist(user_id, new_name.strip())
                st.success(f"Created \u2018{new_name.strip()}\u2019")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

if not watchlists:
    st.info("👉 No watchlists yet. Create one using the form on the right.")
    st.stop()

wl_names = [w["name"] for w in watchlists]
wl_ids   = {w["name"]: w["id"] for w in watchlists}

with col_sel:
    chosen_name = st.selectbox("📝 Select watchlist", wl_names)

chosen_id = wl_ids[chosen_name]

# ---------------------------------------------------------------------------
# Rename / delete
# ---------------------------------------------------------------------------
with st.expander("⚙️ Manage watchlist", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        with st.form("rename_form", clear_on_submit=True):
            new_nm = st.text_input("Rename to", value=chosen_name)
            if st.form_submit_button("✏️ Rename") and new_nm.strip() and new_nm.strip() != chosen_name:
                try:
                    rename_watchlist(chosen_id, new_nm.strip())
                    st.success("Renamed.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with c2:
        if st.button("🗑️ Delete watchlist", type="secondary"):
            if st.session_state.get("_confirm_delete") == chosen_id:
                delete_watchlist(chosen_id)
                st.success("Deleted.")
                st.session_state.pop("_confirm_delete", None)
                st.rerun()
            else:
                st.session_state["_confirm_delete"] = chosen_id
                st.warning("Click again to confirm deletion.")

# ---------------------------------------------------------------------------
# Symbol list
# ---------------------------------------------------------------------------
st.divider()
st.subheader(f"📊 {chosen_name}")

current_syms = get_symbols(chosen_id)

if not current_syms:
    st.info("This watchlist is empty. Add symbols below.")
else:
    for i, sym in enumerate(current_syms):
        r1, r2, r3, r4 = st.columns([4, 1, 1, 1])
        r1.write(f"**{sym}**")
        if r2.button("↑", key=f"up_{sym}", disabled=i == 0):
            ordered = current_syms.copy()
            ordered[i], ordered[i - 1] = ordered[i - 1], ordered[i]
            reorder_symbols(chosen_id, ordered)
            st.rerun()
        if r3.button("↓", key=f"dn_{sym}", disabled=i == len(current_syms) - 1):
            ordered = current_syms.copy()
            ordered[i], ordered[i + 1] = ordered[i + 1], ordered[i]
            reorder_symbols(chosen_id, ordered)
            st.rerun()
        if r4.button("✕", key=f"rm_{sym}"):
            remove_symbol(chosen_id, sym)
            st.rerun()

# ---------------------------------------------------------------------------
# Add symbols
# ---------------------------------------------------------------------------
st.divider()
all_symbols = SYMBOLS
remaining   = [s for s in all_symbols if s not in current_syms]

with st.form("add_sym_form", clear_on_submit=True):
    to_add = st.multiselect(
        "➕ Add symbols",
        options=remaining,
        placeholder="Search for a symbol…",
    )
    if st.form_submit_button("Add selected") and to_add:
        for sym in to_add:
            add_symbol(chosen_id, sym)
        st.success(f"Added {len(to_add)} symbol(s).")
        st.rerun()

# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------
if current_syms:
    st.divider()
    csv_text = export_csv(chosen_id)
    st.download_button(
        "⬇️ Export watchlist CSV",
        data=csv_text.encode(),
        file_name=f"watchlist_{chosen_name}.csv",
        mime="text/csv",
    )
