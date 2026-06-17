"""Shared Streamlit UI helper functions used across all tab modules.

All functions here are thin wrappers over st.markdown / st.divider so that
individual tab modules don’t have to repeat boilerplate.
"""
from __future__ import annotations

import streamlit as st


def hero(title: str, subtitle: str = "") -> None:
    """Render a page/section hero heading with optional subtitle."""
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)


def sec(label: str) -> None:
    """Render a section sub-heading."""
    st.markdown(f"### {label}")


def divider() -> None:
    """Render a horizontal rule divider."""
    st.markdown("---")


def closed_banner(
    market_open: bool,
    market_status: str,
    last_close_label: str,
) -> None:
    """Show a warning banner when NSE is closed."""
    if not market_open:
        msg = f"⏰ NSE is closed — {market_status}"
        if last_close_label:
            msg += f" | {last_close_label}"
        st.info(msg)
