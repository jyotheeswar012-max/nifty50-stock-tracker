"""
utils/supabase_auth.py

Full authentication layer backed by Supabase (free tier).

Features:
  - register(email, password, full_name)  -> (ok, message)
  - login(email, password)                -> (ok, user_dict | error_str)
  - logout()                              -> clears session
  - get_current_user()                    -> user dict or None
  - require_login()                       -> redirects if not authed
  - reset_password(email)                 -> (ok, message)
  - update_profile(full_name, phone)      -> (ok, message)

Secrets required in .streamlit/secrets.toml:
  [supabase]
  url         = "https://xxxx.supabase.co"
  anon_key    = "eyJ..."

Supabase setup (5 min, free):
  1. supabase.com -> New Project
  2. Authentication is enabled by default
  3. Copy Project URL + anon key -> secrets
  4. Optional: Add 'phone' column to auth.users via SQL editor:
     ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS raw_user_meta_data jsonb;
"""
from __future__ import annotations
import streamlit as st
from typing import Optional


# ------------------------------------------------------------------ client

@st.cache_resource
def _get_client():
    """Lazily create Supabase client (cached globally)."""
    try:
        from supabase import create_client
        cfg = st.secrets["supabase"]
        return create_client(str(cfg["url"]), str(cfg["anon_key"]))
    except Exception as e:
        return None


def supabase_ready() -> bool:
    return _get_client() is not None


# ------------------------------------------------------------------ auth ops

def register(
    email: str,
    password: str,
    full_name: str = "",
    phone: str = "",
) -> tuple[bool, str]:
    client = _get_client()
    if not client:
        return False, "Supabase not configured. Contact app owner."
    try:
        meta = {"full_name": full_name}
        if phone:
            meta["phone"] = phone
        res = client.auth.sign_up({
            "email":    email,
            "password": password,
            "options":  {"data": meta},
        })
        if res.user:
            return True, "Account created! Check your email to confirm (if email verification is enabled)."
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
        res = client.auth.sign_in_with_password({
            "email":    email,
            "password": password,
        })
        if res.session and res.user:
            user = res.user
            meta = user.user_metadata or {}
            user_dict = {
                "id":         user.id,
                "email":      user.email,
                "full_name":  meta.get("full_name", user.email.split("@")[0]),
                "phone":      meta.get("phone", ""),
                "token":      res.session.access_token,
            }
            # Store in session
            st.session_state["sb_user"]   = user_dict
            st.session_state["sb_authed"] = True
            return True, user_dict
        return False, "Invalid credentials."
    except Exception as e:
        msg = str(e).lower()
        if "invalid" in msg or "credentials" in msg or "wrong" in msg:
            return False, "Incorrect email or password."
        if "not confirmed" in msg or "email" in msg and "confirm" in msg:
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
        # Update session state
        st.session_state["sb_user"]["full_name"] = full_name or user["full_name"]
        st.session_state["sb_user"]["phone"]     = phone     or user["phone"]
        return True, "Profile updated."
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------------ guard

def require_login(redirect_page: str = "pages/00_🔐_Login.py") -> dict:
    """
    Call at the top of every page.
    If not logged in: shows a gate and calls st.stop().
    If logged in: returns the user dict.
    """
    user = get_current_user()
    if user:
        return user

    # Gate UI
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
      <div class="gate-sub">Please sign in to access this page.</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link(redirect_page, label="➡️ Sign In / Create Account", icon="🔐")
    st.stop()
