"""Streamlit authentication UI — Login / Register.

Supported auth methods:
  📧 Email + Password  : full Firebase REST flow (works everywhere)
  📱 Phone SMS OTP     : Firebase JS SDK sends SMS in-browser (handles
                          reCAPTCHA automatically), Python verifies code

Phone OTP flow detail:
  1. User enters phone number
  2. A Firebase JS SDK iframe renders, fires signInWithPhoneNumber(),
     completes invisible reCAPTCHA, sends the SMS, and outputs the
     verificationId (sessionInfo) into a textarea
  3. User copies verificationId into a Streamlit text_input
     (or it auto-fills via the widget)
  4. User enters the 6-digit SMS code
  5. Python calls verify_phone_otp(verificationId, code) via REST
  6. On success → set_current_user() → app unlocks
"""
from __future__ import annotations

import re
import streamlit as st

from utils.firebase_auth import (
    register_email, login_email,
    verify_phone_otp,
    send_password_reset,
    get_current_user, set_current_user, logout,
    _friendly_error, _api_key,
)
from utils.phone_otp_component import render_send_otp_widget


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _valid_email(v: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", v.strip()))


def _valid_phone(v: str) -> bool:
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
    if get_current_user() is not None:
        return
    _render_auth_page()
    st.stop()


def render_logout_button() -> None:
    user = get_current_user()
    if user is None:
        return
    display = user.get("email") or user.get("phone") or "User"
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
        mode_tab, reg_tab = st.tabs(["🔑 Login", "📝 Register"])
        with mode_tab:
            _login_form()
        with reg_tab:
            _register_form()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def _login_form() -> None:
    method = st.radio("Login with", ["📧 Email", "📱 Phone OTP"], horizontal=True, key="_fb_login_method")
    st.markdown("")
    if method == "📧 Email":
        _email_login()
    else:
        _phone_otp_flow(prefix="login")


def _email_login() -> None:
    email = st.text_input("Email", placeholder="you@example.com", key="_fb_li_email")
    pwd   = st.text_input("Password", type="password", placeholder="Your password", key="_fb_li_pwd")

    c1, c2 = st.columns(2)
    login_btn  = c1.button("Login",             type="primary", use_container_width=True, key="_fb_li_btn")
    forgot_btn = c2.button("Forgot password?",   use_container_width=True,               key="_fb_forgot_btn")

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
# Shared phone OTP flow (used by both Login and Register tabs)
# ---------------------------------------------------------------------------

def _phone_otp_flow(prefix: str) -> None:
    """
    Reusable two-step phone OTP widget.

    prefix = 'login' or 'reg'  — keeps session_state keys separate per tab.

    Step 1: enter phone → show JS widget (sends SMS + outputs verificationId)
    Step 2: paste verificationId + enter 6-digit OTP → verify → login/register
    """
    phone_key   = f"_fb_otp_phone_{prefix}"
    sent_key    = f"_fb_otp_sent_{prefix}"    # bool flag: widget rendered

    # ---- Step 1: Phone entry ------------------------------------------------
    if not st.session_state.get(sent_key):
        phone = st.text_input(
            "Mobile Number", placeholder="+91 98765 43210",
            key=f"_fb_otp_phone_input_{prefix}",
        )
        action = "Login" if prefix == "login" else "Create Account"
        st.caption("📌 Firebase sends a real SMS OTP. No extra gateway needed.")

        if st.button(f"📲 Send OTP & {action}", type="primary",
                     use_container_width=True, key=f"_fb_send_otp_{prefix}"):
            if not phone:
                st.error("Please enter your mobile number.")
            elif not _valid_phone(phone):
                st.error("Enter a valid 10-digit Indian mobile number (e.g. +91 98765 43210).")
            else:
                st.session_state[phone_key] = _normalise_phone(phone)
                st.session_state[sent_key]  = True
                st.rerun()

    # ---- Step 2: JS widget + OTP verify ------------------------------------
    else:
        phone = st.session_state[phone_key]
        api_key = _api_key()

        st.markdown(f"📲 Sending OTP to **{phone}**")
        st.info(
            "🔒 The widget below handles reCAPTCHA and sends the SMS via Firebase. "
            "After the SMS is sent, the **Session Token** box auto-fills. "
            "Copy it into the field that appears, then enter your 6-digit OTP."
        )

        # Render the Firebase JS SDK widget inside an iframe
        # It outputs the verificationId into the paste box
        verification_id = render_send_otp_widget(api_key, phone)

        if verification_id:
            otp = st.text_input(
                "6-digit OTP from SMS", placeholder="123456",
                max_chars=6, key=f"_fb_otp_code_{prefix}",
            )
            col_v, col_r = st.columns(2)
            verify_btn = col_v.button("✅ Verify", type="primary",
                                       use_container_width=True, key=f"_fb_verify_{prefix}")
            resend_btn = col_r.button("🔄 Start Over", use_container_width=True,
                                       key=f"_fb_resend_{prefix}")

            if verify_btn:
                if not otp or len(otp.strip()) != 6 or not otp.strip().isdigit():
                    st.error("Enter the 6-digit OTP from your SMS.")
                else:
                    with st.spinner("Verifying..."):
                        resp = verify_phone_otp(verification_id, otp.strip())
                    if "error" in resp:
                        st.error(_friendly_error(resp["error"].get("message", "Verification failed.")))
                    else:
                        # Clear OTP state
                        for k in [phone_key, sent_key, "_fb_otp_session_paste"]:
                            st.session_state.pop(k, None)
                        set_current_user({
                            "phone":   resp.get("phoneNumber", phone),
                            "idToken": resp.get("idToken", ""),
                            "uid":     resp.get("localId", ""),
                        })
                        st.success("✅ Phone verified! You are now logged in.")
                        st.rerun()

            if resend_btn:
                for k in [phone_key, sent_key, "_fb_otp_session_paste"]:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            # Session token not yet provided
            col_r = st.columns(1)[0]
            if col_r.button("🔄 Start Over", key=f"_fb_resend_early_{prefix}"):
                for k in [phone_key, sent_key, "_fb_otp_session_paste"]:
                    st.session_state.pop(k, None)
                st.rerun()


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def _register_form() -> None:
    method = st.radio("Register with", ["📧 Email", "📱 Phone OTP"], horizontal=True, key="_fb_reg_method")
    st.markdown("")
    if method == "📧 Email":
        _email_register()
    else:
        _phone_otp_flow(prefix="reg")


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
                st.success("✅ Account created! A verification email has been sent. You can now log in.")
