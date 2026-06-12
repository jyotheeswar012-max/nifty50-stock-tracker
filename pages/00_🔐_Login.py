"""
Page: Login / Register / Logout

This is the entry point for authentication.
After login the user is redirected to the main app.

Supported flows:
  1. Login  — existing user logs in
  2. Register — new user signs up (stored in session; add to secrets for persistence)
  3. Forgot password — reset via username + email
  4. Logout — clears session + cookie
"""
import streamlit as st
from utils.auth import get_authenticator

st.set_page_config(
    page_title="Login — Nifty50 Tracker",
    page_icon="🔐",
    layout="centered",
)

# Hero header
st.markdown("""
<div style="text-align:center; padding: 2rem 0 1rem 0;">
  <h1 style="font-size:2.8rem; margin-bottom:0;">&#128200; Nifty50 Tracker</h1>
  <p style="color:#9e9e9e; font-size:1.1rem;">NSE India • Real-Time • Paper Trading • Alerts</p>
</div>
""", unsafe_allow_html=True)

authenticator = get_authenticator()

# ---- Already logged in ----
if st.session_state.get("authentication_status") is True:
    uname = st.session_state.get("username", "")
    name  = st.session_state.get("name",     uname)
    st.success(f"✅ You are already logged in as **{name}** (`{uname}`).")
    authenticator.logout("🚪 Logout", "main", key="logout_top")
    st.info("👉 Use the sidebar to navigate to any page.")
    st.stop()

# ---- Tabs ----
tab_login, tab_register, tab_forgot = st.tabs(["🔑 Login", "📝 Register", "🔒 Forgot Password"])

# ===== LOGIN =====
with tab_login:
    st.markdown("### Welcome back!")
    try:
        name, auth_status, username = authenticator.login(
            fields={
                "Form name": "Login",
                "Username":  "Username",
                "Password":  "Password",
                "Login":     "Login →",
            },
            location="main",
        )
    except Exception as e:
        st.error(f"Login error: {e}")
        name = auth_status = username = None

    if auth_status is True:
        st.success(f"✅ Welcome, **{name}**! Redirecting...")
        st.balloons()
        st.info("👉 Use the **sidebar** to navigate the app.")
    elif auth_status is False:
        st.error("❌ Incorrect username or password.")
    else:
        st.info("ℹ️ Enter your credentials above.")

# ===== REGISTER =====
with tab_register:
    st.markdown("### Create a new account")
    st.caption("💡 After registering, ask the app owner to add your credentials to Secrets for persistence across sessions.")
    try:
        reg_result = authenticator.register_user(
            fields={
                "Form name":        "Register",
                "First name":       "First Name",
                "Last name":        "Last Name",
                "Username":         "Choose a Username",
                "Password":         "Password",
                "Repeat password":  "Confirm Password",
                "Register":         "Create Account →",
                "Email":            "Email Address",
            },
            location="main",
            pre_authorization=False,
        )
        if reg_result:
            email_of_reg = reg_result[1] if isinstance(reg_result, tuple) and len(reg_result) > 1 else ""
            st.success("✅ Account created! You can now log in from the Login tab.")
            if email_of_reg:
                st.info(f"📧 Registered email: **{email_of_reg}**")
    except Exception as e:
        if "already" in str(e).lower():
            st.warning("⚠️ That username is already taken. Please choose another.")
        elif "do not match" in str(e).lower():
            st.error("❌ Passwords do not match.")
        else:
            st.info(str(e))

# ===== FORGOT PASSWORD =====
with tab_forgot:
    st.markdown("### Reset your password")
    try:
        fp_result = authenticator.forgot_password(
            fields={
                "Form name": "Forgot Password",
                "Username":  "Username",
                "Submit":    "Send Reset Link",
            },
            location="main",
        )
        if fp_result:
            username_fp, email_fp, new_pw = fp_result if len(fp_result) == 3 else (None, None, None)
            if username_fp:
                st.success(f"✅ A new temporary password has been generated.")
                st.warning(f"🔒 Temp password: `{new_pw}` — change it after logging in.")
                st.caption(f"Username: `{username_fp}` | Email: `{email_fp}`")
    except Exception as e:
        st.info(str(e))
