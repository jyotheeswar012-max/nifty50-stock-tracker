"""Streamlit authentication UI — Login / Register with email or phone.

Call `auth_gate()` at the top of app.py (after st.set_page_config).
It renders a login/register form and blocks the rest of the app until
the user is authenticated.

Usage in app.py:
    from utils.auth_ui import auth_gate
    auth_gate()          # blocks until authenticated
    # ... rest of app ...
"""
from __future__ import annotations

import re
import streamlit as st

from utils.firebase_auth import (
    register_email, login_email,
    register_phone, login_phone,
    send_password_reset,
    get_current_user, set_current_user, logout,
    _friendly_error,
)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _valid_email(v: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", v.strip()))


def _valid_phone(v: str) -> bool:
    """Accept formats: +91XXXXXXXXXX, 91XXXXXXXXXX, 10-digit Indian mobile."""
    digits = re.sub(r"[\s\-()]", "", v)
    return bool(re.match(r"^(\+91|91)?[6-9]\d{9}$", digits))


def _normalise_phone(v: str) -> str:
    digits = re.sub(r"[\s\-()]", "", v)
    if digits.startswith("+"):
        return digits
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    return "+91" + digits.lstrip("91")


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def auth_gate() -> None:
    """
    Render the auth wall.  If the user is already logged in (session_state),
    returns immediately (app continues rendering).  Otherwise shows the
    login / register UI and calls st.stop() to halt the rest of app.py.
    """
    if get_current_user() is not None:
        return  # already authenticated

    _render_auth_page()
    st.stop()  # halt — app.py body does not execute until authenticated


def render_logout_button() -> None:
    """Render a logout button in the sidebar (call from app.py sidebar block)."""
    user = get_current_user()
    if user is None:
        return
    display = user.get("email") or user.get("phone") or "User"
    st.sidebar.markdown(f"👤 **{display}**")
    if st.sidebar.button("🚪 Logout", key="_fb_logout_btn"):
        logout()
        st.rerun()


# ---------------------------------------------------------------------------
# Internal UI
# ---------------------------------------------------------------------------

def _render_auth_page() -> None:
    # Centered narrow layout
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("## 📈 NSE & Nifty 50 Tracker")
        st.markdown("### 🔐 Sign in to continue")
        st.markdown("---")

        mode_tab, reg_tab = st.tabs(["🔑 Login", "📝 Register"])

        with mode_tab:
            _login_form()

        with reg_tab:
            _register_form()


def _login_form() -> None:
    method = st.radio("Login with", ["📧 Email", "📱 Phone"], horizontal=True, key="_fb_login_method")
    st.markdown("")

    if method == "📧 Email":
        email = st.text_input("Email", placeholder="you@example.com", key="_fb_li_email")
        pwd   = st.text_input("Password", type="password", placeholder="Your password", key="_fb_li_pwd")

        col_login, col_forgot = st.columns([1, 1])
        with col_login:
            login_btn = st.button("Login", type="primary", use_container_width=True, key="_fb_li_btn")
        with col_forgot:
            forgot_btn = st.button("Forgot password?", use_container_width=True, key="_fb_forgot_btn")

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
                    set_current_user({"email": email.strip(), "idToken": resp.get("idToken", ""), "uid": resp.get("localId", "")})
                    st.success("✅ Logged in!")
                    st.rerun()

        if forgot_btn:
            if not email:
                st.warning("Enter your email above first, then click Forgot password.")
            elif not _valid_email(email):
                st.error("Enter a valid email address.")
            else:
                with st.spinner("Sending reset email..."):
                    resp = send_password_reset(email.strip())
                if "error" in resp:
                    st.error(_friendly_error(resp["error"].get("message", "Failed.")))
                else:
                    st.success(f"Password reset email sent to {email}.")

    else:  # Phone
        phone = st.text_input("Mobile Number", placeholder="+91 98765 43210", key="_fb_li_phone")
        pwd   = st.text_input("Password", type="password", placeholder="Your password", key="_fb_li_phone_pwd")

        if st.button("Login", type="primary", use_container_width=True, key="_fb_li_phone_btn"):
            if not phone or not pwd:
                st.error("Please fill in all fields.")
            elif not _valid_phone(phone):
                st.error("Enter a valid 10-digit Indian mobile number (e.g. +91 98765 43210).")
            else:
                norm = _normalise_phone(phone)
                with st.spinner("Signing in..."):
                    resp = login_phone(norm, pwd)
                if "error" in resp:
                    st.error(_friendly_error(resp["error"].get("message", "Login failed.")))
                else:
                    set_current_user({"phone": norm, "idToken": resp.get("idToken", ""), "uid": resp.get("localId", "")})
                    st.success("✅ Logged in!")
                    st.rerun()


def _register_form() -> None:
    method = st.radio("Register with", ["📧 Email", "📱 Phone"], horizontal=True, key="_fb_reg_method")
    st.markdown("")

    if method == "📧 Email":
        email  = st.text_input("Email", placeholder="you@example.com", key="_fb_reg_email")
        pwd    = st.text_input("Password", type="password", placeholder="Min 6 characters", key="_fb_reg_pwd")
        pwd2   = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="_fb_reg_pwd2")

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
                    st.success("✅ Account created! A verification email has been sent. You can now log in.")

    else:  # Phone
        phone  = st.text_input("Mobile Number", placeholder="+91 98765 43210", key="_fb_reg_phone")
        pwd    = st.text_input("Password", type="password", placeholder="Min 6 characters", key="_fb_reg_phone_pwd")
        pwd2   = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="_fb_reg_phone_pwd2")

        st.caption("📌 Your phone number is used as your login identifier.")

        if st.button("Create Account", type="primary", use_container_width=True, key="_fb_reg_phone_btn"):
            if not phone or not pwd or not pwd2:
                st.error("Please fill in all fields.")
            elif not _valid_phone(phone):
                st.error("Enter a valid 10-digit Indian mobile number (e.g. +91 98765 43210).")
            elif len(pwd) < 6:
                st.error("Password must be at least 6 characters.")
            elif pwd != pwd2:
                st.error("Passwords do not match.")
            else:
                norm = _normalise_phone(phone)
                with st.spinner("Creating account..."):
                    resp = register_phone(norm, pwd)
                if "error" in resp:
                    st.error(_friendly_error(resp["error"].get("message", "Registration failed.")))
                else:
                    st.success("✅ Account created! You can now log in with your phone number and password.")
