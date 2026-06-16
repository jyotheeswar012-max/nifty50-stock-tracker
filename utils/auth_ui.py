"""Streamlit authentication UI — Login / Register with email+password or phone SMS OTP.

Call `auth_gate()` at the top of app.py (after st.set_page_config).
It renders a login/register form and blocks the rest of the app until
the user is authenticated.

Auth modes supported:
  - Email + Password   : standard Firebase email/password flow
  - Phone SMS OTP      : Firebase native phone auth (no 3rd-party SMS gateway)
                         Step 1 → enter phone → click "Send OTP" → Firebase sends SMS
                         Step 2 → enter 6-digit code → click "Verify" → logged in

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
    send_phone_otp, verify_phone_otp,
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
    """Accept: +91XXXXXXXXXX, 91XXXXXXXXXX, 10-digit Indian mobile."""
    digits = re.sub(r"[\s\-()]", "", v)
    return bool(re.match(r"^(\+91|91)?[6-9]\d{9}$", digits))


def _normalise_phone(v: str) -> str:
    digits = re.sub(r"[\s\-()]", "", v)
    if digits.startswith("+91"):
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
        return
    _render_auth_page()
    st.stop()


def render_logout_button() -> None:
    """Render a logout button in the sidebar."""
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


# ---------------------------------------------------------------------------
# Login forms
# ---------------------------------------------------------------------------

def _login_form() -> None:
    method = st.radio("Login with", ["📧 Email", "📱 Phone OTP"], horizontal=True, key="_fb_login_method")
    st.markdown("")

    if method == "📧 Email":
        _email_login()
    else:
        _phone_otp_login()


def _email_login() -> None:
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
                set_current_user({
                    "email": email.strip(),
                    "idToken": resp.get("idToken", ""),
                    "uid": resp.get("localId", ""),
                })
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


def _phone_otp_login() -> None:
    """
    Two-step phone OTP login:
      Step 1 — user enters phone number → click Send OTP
      Step 2 — user enters 6-digit code  → click Verify & Login
    Session state keys used:
      _fb_otp_session_login   : sessionInfo token from Firebase
      _fb_otp_phone_login     : normalised phone number
    """
    # Step 1: Phone input
    if "_fb_otp_session_login" not in st.session_state:
        phone = st.text_input(
            "Mobile Number", placeholder="+91 98765 43210",
            key="_fb_li_phone",
        )
        st.caption("You will receive a 6-digit SMS OTP from Firebase.")

        if st.button("📲 Send OTP", type="primary", use_container_width=True, key="_fb_li_send_otp"):
            if not phone:
                st.error("Please enter your mobile number.")
            elif not _valid_phone(phone):
                st.error("Enter a valid 10-digit Indian mobile number (e.g. +91 98765 43210).")
            else:
                norm = _normalise_phone(phone)
                with st.spinner("Sending OTP via SMS..."):
                    resp = send_phone_otp(norm)
                if "error" in resp:
                    st.error(_friendly_error(resp["error"].get("message", "Failed to send OTP.")))
                else:
                    st.session_state["_fb_otp_session_login"] = resp["sessionInfo"]
                    st.session_state["_fb_otp_phone_login"]   = norm
                    st.rerun()

    # Step 2: OTP verification
    else:
        phone = st.session_state["_fb_otp_phone_login"]
        st.info(f"OTP sent to **{phone}**. Check your SMS.")
        otp = st.text_input(
            "Enter 6-digit OTP", placeholder="123456",
            max_chars=6, key="_fb_li_otp_code",
        )
        col_verify, col_resend = st.columns([1, 1])
        with col_verify:
            verify_btn = st.button("✅ Verify & Login", type="primary", use_container_width=True, key="_fb_li_verify")
        with col_resend:
            resend_btn = st.button("🔄 Resend OTP", use_container_width=True, key="_fb_li_resend")

        if verify_btn:
            if not otp or len(otp.strip()) != 6 or not otp.strip().isdigit():
                st.error("Enter the 6-digit OTP from your SMS.")
            else:
                with st.spinner("Verifying OTP..."):
                    resp = verify_phone_otp(
                        st.session_state["_fb_otp_session_login"],
                        otp.strip(),
                    )
                if "error" in resp:
                    st.error(_friendly_error(resp["error"].get("message", "Verification failed.")))
                else:
                    # Clear OTP state and log in
                    st.session_state.pop("_fb_otp_session_login", None)
                    st.session_state.pop("_fb_otp_phone_login", None)
                    set_current_user({
                        "phone": resp.get("phoneNumber", phone),
                        "idToken": resp.get("idToken", ""),
                        "uid": resp.get("localId", ""),
                    })
                    st.success("✅ Phone verified and logged in!")
                    st.rerun()

        if resend_btn:
            # Clear session to go back to step 1
            st.session_state.pop("_fb_otp_session_login", None)
            st.session_state.pop("_fb_otp_phone_login", None)
            st.rerun()


# ---------------------------------------------------------------------------
# Register forms
# ---------------------------------------------------------------------------

def _register_form() -> None:
    method = st.radio("Register with", ["📧 Email", "📱 Phone OTP"], horizontal=True, key="_fb_reg_method")
    st.markdown("")

    if method == "📧 Email":
        _email_register()
    else:
        _phone_otp_register()


def _email_register() -> None:
    email = st.text_input("Email", placeholder="you@example.com", key="_fb_reg_email")
    pwd   = st.text_input("Password", type="password", placeholder="Min 6 characters", key="_fb_reg_pwd")
    pwd2  = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="_fb_reg_pwd2")

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


def _phone_otp_register() -> None:
    """
    Phone registration via OTP:
      Step 1 — enter phone → Send OTP
      Step 2 — enter 6-digit code → Verify → account created + logged in
    Firebase creates the account automatically on first successful
    phone verification (no separate signUp needed for phone auth).
    """
    if "_fb_otp_session_reg" not in st.session_state:
        phone = st.text_input(
            "Mobile Number", placeholder="+91 98765 43210",
            key="_fb_reg_phone",
        )
        st.caption("📌 Firebase will send a 6-digit OTP to this number. Your account is created automatically on verification.")

        if st.button("📲 Send OTP", type="primary", use_container_width=True, key="_fb_reg_send_otp"):
            if not phone:
                st.error("Please enter your mobile number.")
            elif not _valid_phone(phone):
                st.error("Enter a valid 10-digit Indian mobile number (e.g. +91 98765 43210).")
            else:
                norm = _normalise_phone(phone)
                with st.spinner("Sending OTP via SMS..."):
                    resp = send_phone_otp(norm)
                if "error" in resp:
                    st.error(_friendly_error(resp["error"].get("message", "Failed to send OTP.")))
                else:
                    st.session_state["_fb_otp_session_reg"] = resp["sessionInfo"]
                    st.session_state["_fb_otp_phone_reg"]   = norm
                    st.rerun()

    else:
        phone = st.session_state["_fb_otp_phone_reg"]
        st.info(f"OTP sent to **{phone}**. Check your SMS.")
        otp = st.text_input(
            "Enter 6-digit OTP", placeholder="123456",
            max_chars=6, key="_fb_reg_otp_code",
        )
        col_verify, col_resend = st.columns([1, 1])
        with col_verify:
            verify_btn = st.button("✅ Verify & Create Account", type="primary", use_container_width=True, key="_fb_reg_verify")
        with col_resend:
            resend_btn = st.button("🔄 Resend OTP", use_container_width=True, key="_fb_reg_resend")

        if verify_btn:
            if not otp or len(otp.strip()) != 6 or not otp.strip().isdigit():
                st.error("Enter the 6-digit OTP from your SMS.")
            else:
                with st.spinner("Verifying OTP and creating account..."):
                    resp = verify_phone_otp(
                        st.session_state["_fb_otp_session_reg"],
                        otp.strip(),
                    )
                if "error" in resp:
                    st.error(_friendly_error(resp["error"].get("message", "Verification failed.")))
                else:
                    st.session_state.pop("_fb_otp_session_reg", None)
                    st.session_state.pop("_fb_otp_phone_reg", None)
                    set_current_user({
                        "phone": resp.get("phoneNumber", phone),
                        "idToken": resp.get("idToken", ""),
                        "uid": resp.get("localId", ""),
                    })
                    st.success("✅ Account created and logged in!")
                    st.rerun()

        if resend_btn:
            st.session_state.pop("_fb_otp_session_reg", None)
            st.session_state.pop("_fb_otp_phone_reg", None)
            st.rerun()
