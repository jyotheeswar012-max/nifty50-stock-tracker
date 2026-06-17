"""Shared UI helper functions used by all page modules.

Keeping these here (rather than in app.py) means page modules never need
to import from app.py, avoiding circular imports.
"""
import streamlit as st
from utils.calculations import safe_float


def hero(title: str, sub: str = "") -> None:
    st.subheader(title)
    if sub:
        st.caption(sub)


def sec(label: str) -> None:
    st.markdown("**" + label + "**")


def divider() -> None:
    st.markdown("---")


def closed_banner(market_open: bool, market_status: str, last_close_label: str) -> None:
    if not market_open:
        st.warning(
            "NSE CLOSED \u2014 "
            + market_status
            + (" | " + last_close_label if last_close_label else "")
            + " | Showing last closing prices"
        )


def show_pl_result(pl) -> None:
    pl = safe_float(pl)
    if pl > 0:
        st.success("GAIN  Rs." + format(pl, ",.2f"))
    elif pl < 0:
        st.error("LOSS  Rs." + format(abs(pl), ",.2f"))
    else:
        st.info("No Change")
