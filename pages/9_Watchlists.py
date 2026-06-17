"""
pages/9_Watchlists.py  –  Persistent Watchlist Manager v2

Features:
  • Multiple named watchlists per user
  • Add / remove symbols
  • Create / delete lists
  • Live mini-stats (last price, day change) for each symbol
  • Export watchlist as CSV
  • Storage: SQLite → JSON → session_state (auto-selected)
"""
import streamlit as st
import pandas as pd

from utils.watchlist import (
    get_all_watchlists, load_watchlist, add_symbol, remove_symbol,
    create_named_list, delete_named_list,
)
from utils.data import get_last_price, get_stock_data
from utils.constants import NIFTY50_SYMBOLS
from utils.auth_ui import require_login

require_login()

st.set_page_config(page_title="Watchlists", page_icon="👁️", layout="wide")
st.title("👁️ Watchlists")
st.caption("Your watchlists are persisted to disk (SQLite) and survive page refreshes and container restarts.")

# ── Determine user ID (Firebase UID or fallback) ─────────────────────────────
user = st.session_state.get("user", {})
uid = user.get("uid", "default") if user else "default"

# ── Sidebar: list management ──────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Your Lists")
    all_lists = get_all_watchlists(uid)
    list_names = list(all_lists.keys()) or ["Default"]

    selected_list = st.selectbox("Active Watchlist", list_names)

    st.divider()
    st.subheader("Create New List")
    new_list_name = st.text_input("List Name", placeholder="e.g. IT Sector")
    if st.button("➕ Create", use_container_width=True) and new_list_name.strip():
        create_named_list(new_list_name.strip(), uid)
        st.rerun()

    if selected_list != "Default":
        if st.button(f"🗑️ Delete '{selected_list}'",
                     use_container_width=True, type="secondary"):
            delete_named_list(selected_list, uid)
            st.rerun()

    st.divider()
    st.subheader("Add Symbol")
    new_sym = st.selectbox("From Nifty 50", ["— select —"] + NIFTY50_SYMBOLS, key="add_nifty")
    if st.button("Add from Nifty 50") and new_sym != "— select —":
        add_symbol(new_sym, uid, selected_list)
        st.rerun()

    custom_sym = st.text_input("Custom Symbol (e.g. INFY.NS)").upper().strip()
    if st.button("Add Custom") and custom_sym:
        add_symbol(custom_sym, uid, selected_list)
        st.rerun()

# ── Main panel ────────────────────────────────────────────────────────────────
watchlist = load_watchlist(uid, selected_list)

if not watchlist:
    st.info(f"**'{selected_list}'** is empty. Add symbols using the sidebar.")
else:
    st.subheader(f"{selected_list}  ({len(watchlist)} symbols)")

    # Load live data for all symbols
    rows = []
    with st.spinner("Fetching latest prices..."):
        for sym in watchlist:
            try:
                price_info = get_last_price(sym)
                rows.append({
                    "Symbol": sym,
                    "Price (₹)": price_info.get("price", "N/A"),
                    "Change (%)": price_info.get("change_pct", "N/A"),
                    "Day High": price_info.get("day_high", "N/A"),
                    "Day Low": price_info.get("day_low", "N/A"),
                })
            except Exception:
                rows.append({"Symbol": sym, "Price (₹)": "N/A",
                             "Change (%)": "N/A", "Day High": "N/A", "Day Low": "N/A"})

    df = pd.DataFrame(rows)

    # Colour-code change column
    def colour_change(val):
        try:
            v = float(val)
            return "color: #4CAF50" if v > 0 else ("color: #F44336" if v < 0 else "")
        except Exception:
            return ""

    styled = df.style.applymap(colour_change, subset=["Change (%)"])
    st.dataframe(styled, use_container_width=True, height=400)

    # Per-symbol remove buttons
    st.subheader("Remove Symbols")
    cols = st.columns(min(len(watchlist), 5))
    for i, sym in enumerate(watchlist):
        if cols[i % 5].button(f"✕ {sym}", key=f"rm_{sym}_{selected_list}"):
            remove_symbol(sym, uid, selected_list)
            st.rerun()

    # Export
    csv = df.to_csv(index=False).encode()
    st.download_button(
        "⬇ Export as CSV", csv,
        file_name=f"watchlist_{selected_list}.csv",
        mime="text/csv",
    )
