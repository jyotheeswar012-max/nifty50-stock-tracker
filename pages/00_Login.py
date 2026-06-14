"""
Redirect shim — forwards to the canonical Login page.
This file exists only so old bookmarks don't 404.
"""
import streamlit as st
st.switch_page("pages/09_Login.py")
