"""Firebase Authentication helpers using the Firebase REST API.

No Firebase Admin SDK required — uses the public Identity Toolkit REST API
so credentials are stored only in Streamlit secrets (never in code).

Required secrets in .streamlit/secrets.toml:
    [firebase]
    api_key = "YOUR_WEB_API_KEY"

Phone OTP flow (Firebase Phone Auth via REST):
    1. send_phone_otp(phone)           → returns sessionInfo (OTP session token)
    2. verify_phone_otp(session, code) → returns idToken + uid on success

Public endpoints used:
    POST https://identitytoolkit.googleapis.com/v1/accounts:signUp
    POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword
    POST https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode
    POST https://identitytoolkit.googleapis.com/v1/accounts:lookup
    POST https://identitytoolkit.googleapis.com/v1/accounts:update
    POST https://www.googleapis.com/identitytoolkit/v3/relyingparty/sendVerificationCode
    POST https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPhoneNumber
"""
from __future__ import annotations

import requests
import streamlit as st

BASE   = "https://identitytoolkit.googleapis.com/v1/accounts"
BASE_V3 = "https://www.googleapis.com/identitytoolkit/v3/relyingparty"


def _api_key() -> str:
    """Read Firebase Web API key from Streamlit secrets."""
    try:
        return st.secrets["firebase"]["api_key"]
    except Exception:
        return ""


def _post(endpoint: str, payload: dict) -> dict:
    """POST to Firebase v1 REST API and return JSON response or error dict."""
    key = _api_key()
    if not key:
        return {"error": {"message": "FIREBASE_API_KEY_MISSING — add it to .streamlit/secrets.toml"}}
    try:
        r = requests.post(
            f"{BASE}:{endpoint}?key={key}",
            json=payload,
            timeout=10,
        )
        return r.json()
    except Exception as exc:
        return {"error": {"message": str(exc)}}


def _post_v3(endpoint: str, payload: dict) -> dict:
    """POST to Firebase v3 relyingparty REST API (phone OTP endpoints)."""
    key = _api_key()
    if not key:
        return {"error": {"message": "FIREBASE_API_KEY_MISSING — add it to .streamlit/secrets.toml"}}
    try:
        r = requests.post(
            f"{BASE_V3}/{endpoint}?key={key}",
            json=payload,
            timeout=15,
        )
        return r.json()
    except Exception as exc:
        return {"error": {"message": str(exc)}}


# ---------------------------------------------------------------------------
# Email + Password Auth
# ---------------------------------------------------------------------------

def register_email(email: str, password: str) -> dict:
    """
    Create a new user with email + password.
    Returns Firebase user dict on success, or dict with 'error' key.
    Automatically sends a verification email after registration.
    """
    resp = _post("signUp", {"email": email, "password": password, "returnSecureToken": True})
    if "error" not in resp:
        _post("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": resp.get("idToken", "")})
    return resp


def login_email(email: str, password: str) -> dict:
    """
    Sign in with email + password.
    Returns Firebase user dict with idToken on success.
    """
    return _post(
        "signInWithPassword",
        {"email": email, "password": password, "returnSecureToken": True},
    )


def send_password_reset(email: str) -> dict:
    """Send a password-reset email."""
    return _post("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})


# ---------------------------------------------------------------------------
# Phone OTP Auth  (Firebase REST v3 — native SMS OTP, no gateway needed)
# ---------------------------------------------------------------------------
# Firebase handles SMS delivery natively for Indian numbers (+91) when
# Phone Authentication is enabled in Firebase console → Authentication →
# Sign-in method → Phone.  No Twilio or Fast2SMS account required.
#
# Flow:
#   1. send_phone_otp(e164_phone)         → {"sessionInfo": "..."} on success
#   2. verify_phone_otp(sessionInfo, code) → {"idToken": ..., "localId": ..., "phoneNumber": ...}
#
# The reCAPTCHA requirement:  Firebase normally enforces reCAPTCHA for the
# sendVerificationCode call from web clients.  When calling from a trusted
# server (Streamlit Cloud / backend), pass recaptchaToken="" — Firebase
# will honour it for test numbers and may require a reCAPTCHA bypass token
# for production.  For Streamlit apps the easiest production path is to
# whitelist your Streamlit Cloud domain in Firebase console → Auth →
# Settings → Authorised domains.
# ---------------------------------------------------------------------------

def send_phone_otp(e164_phone: str) -> dict:
    """
    Send an SMS OTP to the given E.164 phone number (+91XXXXXXXXXX).

    Returns:
        {"sessionInfo": "<opaque token>"}  on success
        {"error": {"message": "..."}}      on failure

    The sessionInfo must be passed to verify_phone_otp() together with
    the 6-digit code the user received.
    """
    resp = _post_v3(
        "sendVerificationCode",
        {
            "phoneNumber": e164_phone,
            "recaptchaToken": "",   # server-side call; reCAPTCHA not enforced
        },
    )
    return resp


def verify_phone_otp(session_info: str, otp_code: str) -> dict:
    """
    Verify the OTP code using the sessionInfo token from send_phone_otp().

    Returns Firebase user dict (idToken, localId, phoneNumber) on success,
    or dict with 'error' key on failure.
    """
    resp = _post_v3(
        "verifyPhoneNumber",
        {
            "sessionInfo": session_info,
            "code": otp_code.strip(),
        },
    )
    return resp


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_current_user() -> dict | None:
    """Return the user dict stored in session_state, or None."""
    return st.session_state.get("_fb_user", None)


def set_current_user(user: dict) -> None:
    """Store authenticated user in session_state."""
    st.session_state["_fb_user"] = user


def logout() -> None:
    """Clear the authenticated user from session_state."""
    st.session_state.pop("_fb_user", None)
    for key in list(st.session_state.keys()):
        if key.startswith("_fb_"):
            del st.session_state[key]


def _friendly_error(msg: str) -> str:
    """Convert Firebase error codes to human-readable messages."""
    table = {
        "EMAIL_EXISTS":                   "This email is already registered. Please log in.",
        "WEAK_PASSWORD":                  "Password must be at least 6 characters.",
        "EMAIL_NOT_FOUND":                "No account found with this email.",
        "INVALID_PASSWORD":               "Incorrect password. Please try again.",
        "INVALID_EMAIL":                  "Invalid email address.",
        "TOO_MANY_ATTEMPTS_TRY_LATER":    "Too many attempts. Please try again later.",
        "USER_DISABLED":                  "This account has been disabled.",
        "INVALID_LOGIN_CREDENTIALS":      "Incorrect email or password.",
        "FIREBASE_API_KEY_MISSING":       "Firebase is not configured. Add your API key to .streamlit/secrets.toml.",
        # Phone OTP errors
        "INVALID_CODE":                   "Incorrect OTP code. Please try again.",
        "SESSION_EXPIRED":                "OTP session expired. Please request a new code.",
        "INVALID_SESSION_INFO":           "OTP session invalid. Please request a new code.",
        "QUOTA_EXCEEDED":                 "SMS quota exceeded. Please try again later.",
        "INVALID_PHONE_NUMBER":           "Invalid phone number. Use E.164 format e.g. +91 98765 43210.",
        "MISSING_PHONE_NUMBER":           "Phone number is required.",
        "CAPTCHA_CHECK_FAILED":           "Security check failed. Please try again.",
    }
    for code, friendly in table.items():
        if code in msg:
            return friendly
    return msg
