"""
utils/auth.py

Centralised authentication helpers using streamlit-authenticator.

User credentials are stored in Streamlit Secrets under [credentials].
New users are registered via the Register tab and their hashed passwords
are stored in st.session_state during the session (no DB needed).

Secrets structure (.streamlit/secrets.toml):

  [credentials.usernames.admin]
  name     = "Admin"
  email    = "admin@example.com"
  password = "$2b$12$..."   # bcrypt hash  — generate with make_hash()

  [cookie]
  name     = "nifty50_auth"
  key      = "some_random_secret_32chars"
  expiry_days = 30
"""
from __future__ import annotations
import streamlit as st

COOKIE_DEFAULTS = {
    "name":         "nifty50_auth",
    "key":          "change_me_to_a_long_random_secret",
    "expiry_days":  30,
}


def _build_config() -> dict:
    """
    Build the config dict expected by streamlit_authenticator.Authenticate.
    Falls back to empty credentials if secrets are not yet configured.
    """
    try:
        creds = dict(st.secrets.get("credentials", {}))
        # Normalize: secrets returns AttrDict, authenticator needs plain dict
        usernames = {}
        for uname, udata in creds.get("usernames", {}).items():
            usernames[uname] = {
                "name":     str(udata.get("name",     uname)),
                "email":    str(udata.get("email",    "")),
                "password": str(udata.get("password", "")),
            }
        creds["usernames"] = usernames
    except Exception:
        creds = {"usernames": {}}

    try:
        cookie = dict(st.secrets.get("cookie", COOKIE_DEFAULTS))
    except Exception:
        cookie = COOKIE_DEFAULTS.copy()

    return {
        "credentials": creds,
        "cookie":      {
            "name":         str(cookie.get("name",         COOKIE_DEFAULTS["name"])),
            "key":          str(cookie.get("key",          COOKIE_DEFAULTS["key"])),
            "expiry_days":  int(cookie.get("expiry_days",  COOKIE_DEFAULTS["expiry_days"])),
        },
    }


def get_authenticator():
    """Return a cached streamlit_authenticator.Authenticate instance."""
    import streamlit_authenticator as stauth

    if "_authenticator" not in st.session_state:
        cfg = _build_config()
        st.session_state["_authenticator"] = stauth.Authenticate(
            cfg["credentials"],
            cfg["cookie"]["name"],
            cfg["cookie"]["key"],
            cfg["cookie"]["expiry_days"],
        )
    return st.session_state["_authenticator"]


def require_login() -> tuple[str | None, bool]:
    """
    Call this at the top of every page.
    Returns (username, is_authenticated).
    If not authenticated, renders a redirect message and calls st.stop().
    """
    auth_status = st.session_state.get("authentication_status")
    username    = st.session_state.get("username", "")

    if auth_status is True:
        return username, True

    # Not logged in — show a friendly gate
    st.warning("🔒 Please **log in** first to access this page.")
    st.page_link("pages/00_🔐_Login.py", label="➡️ Go to Login page", icon="🔐")
    st.stop()
    return None, False


def make_hash(plain_password: str) -> str:
    """Utility: generate a bcrypt hash for a password (use in Python REPL to set up admin)."""
    import bcrypt
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()
