"""Streamlit authentication UI — Login / Register (Email + Password only)."""
from __future__ import annotations

import re
import streamlit as st

from utils.firebase_auth import (
    register_email, login_email,
    send_password_reset,
    get_current_user, set_current_user, logout,
    _friendly_error,
)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _valid_email(v: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", v.strip()))


# ---------------------------------------------------------------------------
# Public entry-points
# ---------------------------------------------------------------------------

def auth_gate() -> None:
    if get_current_user() is not None:
        return
    _render_auth_page()
    st.stop()


def render_logout_button() -> None:
    user = get_current_user()
    if user is None:
        return
    display = user.get("email") or "User"
    st.sidebar.markdown(f"👤 **{display}**")
    if st.sidebar.button("🚪 Logout", key="_fb_logout_btn"):
        logout()
        st.rerun()


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

def _render_auth_page() -> None:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("## 📈 NSE & Nifty 50 Tracker")
        st.markdown("### 🔐 Sign in to continue")
        st.markdown("---")
        login_tab, reg_tab = st.tabs(["🔑 Login", "📝 Register"])
        with login_tab:
            _email_login()
        with reg_tab:
            _email_register()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def _email_login() -> None:
    email = st.text_input("Email", placeholder="you@example.com", key="_fb_li_email")
    pwd   = st.text_input("Password", type="password", placeholder="Your password", key="_fb_li_pwd")

    c1, c2 = st.columns(2)
    login_btn  = c1.button("Login",           type="primary", use_container_width=True, key="_fb_li_btn")
    forgot_btn = c2.button("Forgot password?", use_container_width=True,               key="_fb_forgot_btn")

    if login_btn:
        if not email or not pwd:
            st.error("Please fill in all fields.")
        elif not _valid_email(email):
            st.error("Enter a valid email address.")
        else:
            with st.spinner("Signing in..."):
                resp = login_email(email.strip(), pwd)
            if "error" in resp:
                st.error(_friendly_error(resp["error"].get("message", "Login failed.")))
            else:
                set_current_user({
                    "email":    email.strip(),
                    "idToken": resp.get("idToken", ""),
                    "uid":     resp.get("localId", ""),
                })
                st.success("✅ Logged in!")
                st.rerun()

    if forgot_btn:
        if not email:
            st.warning("Enter your email above first.")
        elif not _valid_email(email):
            st.error("Enter a valid email address.")
        else:
            with st.spinner("Sending reset email..."):
                resp = send_password_reset(email.strip())
            if "error" in resp:
                st.error(_friendly_error(resp["error"].get("message", "Failed.")))
            else:
                st.success(f"Password reset email sent to {email}.")


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def _email_register() -> None:
    email = st.text_input("Email", placeholder="you@example.com", key="_fb_reg_email")
    pwd   = st.text_input("Password",         type="password", placeholder="Min 6 characters", key="_fb_reg_pwd")
    pwd2  = st.text_input("Confirm Password", type="password", placeholder="Repeat password",  key="_fb_reg_pwd2")

    if st.button("Create Account", type="primary", use_container_width=True, key="_fb_reg_btn"):
        if not email or not pwd or not pwd2:
            st.error("Please fill in all fields.")
        elif not _valid_email(email):
            st.error("Enter a valid email address.")
        elif len(pwd) < 6:
            st.error("Password must be at least 6 characters.")
        elif pwd != pwd2:
            st.error("Passwords do not match.")
        else:
            with st.spinner("Creating account..."):
                resp = register_email(email.strip(), pwd)
            if "error" in resp:
                st.error(_friendly_error(resp["error"].get("message", "Registration failed.")))
            else:
                st.success("✅ Account created! You can now log in.")
