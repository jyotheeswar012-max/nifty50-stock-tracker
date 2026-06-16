"""Firebase Authentication helpers using the Firebase REST API.

No Firebase Admin SDK required — uses the public Identity Toolkit REST API
so credentials are stored only in Streamlit secrets (never in code).

Required secrets in .streamlit/secrets.toml:
    [firebase]
    api_key = "YOUR_WEB_API_KEY"

Phone OTP flow:
  The SMS is sent via the Firebase JS SDK running in an in-page iframe
  (see utils/phone_otp_component.py).  The JS SDK handles reCAPTCHA
  automatically.  After the SMS is sent, the browser widget gives back
  a verificationId (sessionInfo).  Python then verifies the code via
  the REST verifyPhoneNumber endpoint.

Public REST endpoints used:
    POST .../accounts:signUp
    POST .../accounts:signInWithPassword
    POST .../accounts:sendOobCode
    POST .../relyingparty/verifyPhoneNumber   (OTP verify only)
"""
from __future__ import annotations

import requests
import streamlit as st

BASE    = "https://identitytoolkit.googleapis.com/v1/accounts"
BASE_V3 = "https://www.googleapis.com/identitytoolkit/v3/relyingparty"


def _api_key() -> str:
    try:
        return st.secrets["firebase"]["api_key"]
    except Exception:
        return ""


def _post(endpoint: str, payload: dict) -> dict:
    key = _api_key()
    if not key:
        return {"error": {"message": "FIREBASE_API_KEY_MISSING — add it to .streamlit/secrets.toml"}}
    try:
        r = requests.post(f"{BASE}:{endpoint}?key={key}", json=payload, timeout=10)
        return r.json()
    except Exception as exc:
        return {"error": {"message": str(exc)}}


def _post_v3(endpoint: str, payload: dict) -> dict:
    key = _api_key()
    if not key:
        return {"error": {"message": "FIREBASE_API_KEY_MISSING — add it to .streamlit/secrets.toml"}}
    try:
        r = requests.post(f"{BASE_V3}/{endpoint}?key={key}", json=payload, timeout=15)
        return r.json()
    except Exception as exc:
        return {"error": {"message": str(exc)}}


# ---------------------------------------------------------------------------
# Email + Password Auth
# ---------------------------------------------------------------------------

def register_email(email: str, password: str) -> dict:
    resp = _post("signUp", {"email": email, "password": password, "returnSecureToken": True})
    if "error" not in resp:
        _post("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": resp.get("idToken", "")})
    return resp


def login_email(email: str, password: str) -> dict:
    return _post("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})


def send_password_reset(email: str) -> dict:
    return _post("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})


# ---------------------------------------------------------------------------
# Phone OTP verify  (SMS is sent by the JS SDK in the browser widget)
# ---------------------------------------------------------------------------

def verify_phone_otp(verification_id: str, otp_code: str) -> dict:
    """
    Verify the 6-digit OTP using the verificationId returned by the
    Firebase JS SDK (signInWithPhoneNumber → result.verificationId).

    Returns Firebase user dict (idToken, localId, phoneNumber) on success.
    """
    return _post_v3(
        "verifyPhoneNumber",
        {"sessionInfo": verification_id, "code": otp_code.strip()},
    )


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_current_user() -> dict | None:
    return st.session_state.get("_fb_user", None)


def set_current_user(user: dict) -> None:
    st.session_state["_fb_user"] = user


def logout() -> None:
    st.session_state.pop("_fb_user", None)
    for key in list(st.session_state.keys()):
        if key.startswith("_fb_"):
            del st.session_state[key]


def _friendly_error(msg: str) -> str:
    table = {
        "EMAIL_EXISTS":                "This email is already registered. Please log in.",
        "WEAK_PASSWORD":               "Password must be at least 6 characters.",
        "EMAIL_NOT_FOUND":             "No account found with this email.",
        "INVALID_PASSWORD":            "Incorrect password. Please try again.",
        "INVALID_EMAIL":               "Invalid email address.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
        "USER_DISABLED":               "This account has been disabled.",
        "INVALID_LOGIN_CREDENTIALS":   "Incorrect email or password.",
        "FIREBASE_API_KEY_MISSING":    "Firebase is not configured. Add your API key to .streamlit/secrets.toml.",
        "INVALID_CODE":                "Incorrect OTP. Please try again.",
        "SESSION_EXPIRED":             "OTP session expired. Please request a new code.",
        "INVALID_SESSION_INFO":        "OTP session invalid. Please request a new code.",
        "QUOTA_EXCEEDED":              "SMS quota exceeded. Please try again later.",
        "INVALID_PHONE_NUMBER":        "Invalid phone number. Use format +91 98765 43210.",
        "CAPTCHA_CHECK_FAILED":        "Security check failed. Please refresh and try again.",
    }
    for code, friendly in table.items():
        if code in msg:
            return friendly
    return msg
