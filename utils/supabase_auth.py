"""
utils/supabase_auth.py
Auth layer backed by Supabase.
Guest mode: anyone can view the app; login is only required to SAVE data.
"""
from __future__ import annotations
import streamlit as st
from typing import Optional


@st.cache_resource
def _get_client():
    try:
        from supabase import create_client
        cfg = st.secrets["supabase"]
        return create_client(str(cfg["url"]), str(cfg["anon_key"]))
    except Exception:
        return None


def supabase_ready() -> bool:
    return _get_client() is not None


# ──────────────────────────────────────────────────────────────── auth ops

def register(email: str, password: str, full_name: str = "", phone: str = "") -> tuple[bool, str]:
    client = _get_client()
    if not client:
        return False, "Supabase not configured. Contact app owner."
    try:
        meta = {"full_name": full_name}
        if phone:
            meta["phone"] = phone
        res = client.auth.sign_up({"email": email, "password": password,
                                    "options": {"data": meta}})
        if res.user:
            return True, "Account created! Check your email to confirm."
        return False, "Registration failed. Please try again."
    except Exception as e:
        msg = str(e).lower()
        if "already registered" in msg or "already exists" in msg:
            return False, "An account with this email already exists."
        if "password" in msg:
            return False, "Password must be at least 6 characters."
        return False, str(e)


def login(email: str, password: str) -> tuple[bool, dict | str]:
    client = _get_client()
    if not client:
        return False, "Supabase not configured."
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.session and res.user:
            user  = res.user
            meta  = user.user_metadata or {}
            udict = {
                "id":        user.id,
                "email":     user.email,
                "full_name": meta.get("full_name", user.email.split("@")[0]),
                "phone":     meta.get("phone", ""),
                "token":     res.session.access_token,
            }
            st.session_state["sb_user"]   = udict
            st.session_state["sb_authed"] = True
            return True, udict
        return False, "Invalid credentials."
    except Exception as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg or "wrong" in msg:
            return False, "Incorrect email or password."
        if "not confirmed" in msg:
            return False, "Please confirm your email before logging in."
        return False, str(e)


def logout() -> None:
    client = _get_client()
    if client:
        try:
            client.auth.sign_out()
        except Exception:
            pass
    for key in ["sb_user", "sb_authed", "user_email", "user_phone",
                "notify_email", "notify_sms", "profile_saved",
                "alerts", "notified_set"]:
        st.session_state.pop(key, None)


def get_current_user() -> Optional[dict]:
    if st.session_state.get("sb_authed") and st.session_state.get("sb_user"):
        return st.session_state["sb_user"]
    return None


def is_guest() -> bool:
    """True when the visitor is NOT logged in."""
    return get_current_user() is None


def reset_password(email: str) -> tuple[bool, str]:
    client = _get_client()
    if not client:
        return False, "Supabase not configured."
    try:
        client.auth.reset_password_email(email)
        return True, f"Password reset email sent to {email}."
    except Exception as e:
        return False, str(e)


def update_profile(full_name: str = "", phone: str = "") -> tuple[bool, str]:
    client = _get_client()
    if not client:
        return False, "Supabase not configured."
    user = get_current_user()
    if not user:
        return False, "Not logged in."
    try:
        meta = {}
        if full_name: meta["full_name"] = full_name
        if phone:     meta["phone"]     = phone
        client.auth.update_user({"data": meta})
        st.session_state["sb_user"]["full_name"] = full_name or user["full_name"]
        st.session_state["sb_user"]["phone"]     = phone     or user["phone"]
        return True, "Profile updated."
    except Exception as e:
        return False, str(e)


# ──────────────────────────────────────────────────────────────── guards

def login_nudge(feature: str = "save your data") -> None:
    """
    Soft, non-blocking banner for guests. Does NOT call st.stop().
    Points to the CORRECT Login page path.
    """
    st.info(
        f"💡 **Sign in to {feature}.** "
        f"You're browsing as a guest — everything is visible but nothing is saved.",
        icon="🔒",
    )
    # Use the ACTUAL filename that exists on disk
    st.page_link("pages/00_🔐_Login.py", label="➡️ Sign In / Create Account", icon="🔐")


def require_login(redirect_page: str = "pages/00_🔐_Login.py") -> dict:
    """
    Hard guard — use ONLY on pages that are 100% useless without an account.
    Returns the user dict when logged in.
    """
    user = get_current_user()
    if user:
        return user

    st.markdown("""
    <style>
    .gate-wrap{display:flex;flex-direction:column;align-items:center;
               justify-content:center;padding:5rem 1rem;text-align:center;}
    .gate-icon{font-size:4rem;margin-bottom:1rem;}
    .gate-title{font-size:2rem;font-weight:700;margin-bottom:.5rem;}
    .gate-sub{color:#9e9e9e;font-size:1.1rem;margin-bottom:2rem;}
    </style>
    <div class="gate-wrap">
      <div class="gate-icon">🔒</div>
      <div class="gate-title">Login Required</div>
      <div class="gate-sub">This page requires an account.</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link(redirect_page, label="➡️ Sign In / Create Account", icon="🔐")
    st.stop()
