"""Firebase Authentication helpers using the Firebase REST API.

No Firebase Admin SDK required — uses the public Identity Toolkit REST API
so credentials are stored only in Streamlit secrets (never in code).

Required secrets in .streamlit/secrets.toml:
    [firebase]
    api_key = "YOUR_WEB_API_KEY"

Optional (for phone OTP — needs Firebase phone auth enabled):
    [firebase]
    api_key            = "YOUR_WEB_API_KEY"
    # Phone OTP is handled client-side via Firebase JS SDK;
    # server-side phone verification uses the same REST endpoint.

Public endpoints used:
    POST https://identitytoolkit.googleapis.com/v1/accounts:signUp
    POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword
    POST https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode
    POST https://identitytoolkit.googleapis.com/v1/accounts:lookup
    POST https://identitytoolkit.googleapis.com/v1/accounts:update
"""
from __future__ import annotations

import requests
import streamlit as st

BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


def _api_key() -> str:
    """Read Firebase Web API key from Streamlit secrets."""
    try:
        return st.secrets["firebase"]["api_key"]
    except Exception:
        return ""


def _post(endpoint: str, payload: dict) -> dict:
    """POST to Firebase REST API and return JSON response or error dict."""
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
        # Send email verification
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
# Phone OTP Auth  (server-side flow via REST)
# ---------------------------------------------------------------------------
# NOTE: Firebase's phone auth is primarily designed for client-side (JS/Android/iOS).
# The REST API does NOT expose a direct server-side "send SMS OTP" endpoint.
# The standard server-side approach is:
#   1. Use the Firebase JS SDK in the browser to trigger reCAPTCHA + send OTP
#   2. Verify the code with signInWithPhoneNumber on the client
#
# For a pure-Python Streamlit app the recommended pattern is:
#   - Use email as the primary auth method (fully supported by REST API)
#   - Optionally link a phone number via the Firebase console after login
#
# The functions below use a workaround: treat phone as an email alias
# (phone@nse-tracker.app) so the same email+password flow is used.
# For true SMS OTP integrate Twilio / Fast2SMS separately.

def register_phone(phone: str, password: str) -> dict:
    """
    Register using phone number as identifier.
    Phone is stored as '{phone}@nse-tracker.app' internally.
    """
    pseudo_email = _phone_to_email(phone)
    return register_email(pseudo_email, password)


def login_phone(phone: str, password: str) -> dict:
    """
    Login using phone number + password.
    """
    pseudo_email = _phone_to_email(phone)
    return login_email(pseudo_email, password)


def _phone_to_email(phone: str) -> str:
    """Map a phone number to a deterministic pseudo-email for Firebase."""
    digits = "".join(c for c in phone if c.isdigit() or c == "+")
    return f"{digits}@nse-tracker.app"


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
    # Also clear any derived state
    for key in list(st.session_state.keys()):
        if key.startswith("_fb_"):
            del st.session_state[key]


def _friendly_error(msg: str) -> str:
    """Convert Firebase error codes to human-readable messages."""
    table = {
        "EMAIL_EXISTS":                   "This email is already registered. Please log in.",
        "WEAK_PASSWORD":                  "Password must be at least 6 characters.",
        "EMAIL_NOT_FOUND":                "No account found with this email/phone.",
        "INVALID_PASSWORD":               "Incorrect password. Please try again.",
        "INVALID_EMAIL":                  "Invalid email address.",
        "TOO_MANY_ATTEMPTS_TRY_LATER":    "Too many attempts. Please try again later.",
        "USER_DISABLED":                  "This account has been disabled.",
        "INVALID_LOGIN_CREDENTIALS":      "Incorrect email/phone or password.",
        "FIREBASE_API_KEY_MISSING":       "Firebase is not configured. Add your API key to .streamlit/secrets.toml.",
    }
    for code, friendly in table.items():
        if code in msg:
            return friendly
    return msg
