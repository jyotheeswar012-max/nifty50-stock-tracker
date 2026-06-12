"""
Page: Login / Register / Forgot Password

Beautiful full-page auth UI backed by Supabase.
Users can sign up, sign in, and reset password entirely from this page.
All credentials are stored in Supabase (not in Streamlit secrets).
"""
import streamlit as st
from utils.supabase_auth import (
    register, login, logout, get_current_user,
    reset_password, supabase_ready,
)

st.set_page_config(
    page_title="Sign In — Nifty50 Tracker",
    page_icon="📈",
    layout="centered",
)

# ------------------------------------------------------------------ CSS
st.markdown("""
<style>
/* Hide default Streamlit chrome on auth page */
[data-testid="stSidebar"] { display: none; }
[data-testid="stHeader"]  { background: transparent; }

/* Page background */
.stApp { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%); }

/* Card */
.auth-card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 24px;
    padding: 2.5rem 2rem;
    margin: 0 auto;
    max-width: 460px;
}

/* Logo area */
.auth-logo {
    text-align: center;
    margin-bottom: 1.8rem;
}
.auth-logo h1 {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00e5ff, #00c853);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.auth-logo p {
    color: #9e9e9e;
    font-size: 0.95rem;
    margin: 4px 0 0 0;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    color: #9e9e9e;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #00e5ff22, #00c85322) !important;
    color: #00e5ff !important;
}

/* Input fields */
.stTextInput input {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    color: white !important;
    padding: 12px 16px !important;
    font-size: 0.95rem !important;
}
.stTextInput input:focus {
    border-color: #00e5ff !important;
    box-shadow: 0 0 0 2px rgba(0,229,255,0.15) !important;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #00e5ff, #00c853) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 12px 0 !important;
    width: 100% !important;
    transition: opacity .2s;
}
.stButton > button[kind="primary"]:hover { opacity: .85; }

/* Divider */
.auth-divider {
    display: flex; align-items: center; gap: 12px;
    color: #555; font-size: .85rem; margin: 1.2rem 0;
}
.auth-divider::before,.auth-divider::after {
    content: ""; flex: 1;
    border-top: 1px solid rgba(255,255,255,0.1);
}

/* Feature pills */
.feature-row {
    display: flex; gap: 8px; justify-content: center;
    flex-wrap: wrap; margin-top: 1.5rem;
}
.feature-pill {
    background: rgba(0,229,255,0.1);
    border: 1px solid rgba(0,229,255,0.2);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: .8rem;
    color: #00e5ff;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ already logged in
user = get_current_user()
if user:
    st.success(f"✅ Already signed in as **{user['full_name']}** ({user['email']})")
    c1, c2 = st.columns(2)
    with c1:
        st.page_link("app.py", label="➡️ Go to Dashboard", icon="📈")
    with c2:
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()
            st.rerun()
    st.stop()

# ------------------------------------------------------------------ service check
if not supabase_ready():
    st.error("❌ Supabase is not configured. See setup guide below.")
    with st.expander("ℹ️ Setup Guide"):
        st.markdown("""
**1. Create a free Supabase project** at [supabase.com](https://supabase.com)

**2. Add to `.streamlit/secrets.toml` or Streamlit Cloud Secrets:**
```toml
[supabase]
url      = "https://xxxxxxxxxxxx.supabase.co"
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```
**3. Redeploy.** Registration & login will work for all users automatically.
        """)

# ------------------------------------------------------------------ hero
st.markdown("""
<div class="auth-logo">
  <h1>📈 Nifty50 Tracker</h1>
  <p>NSE India • Real-Time • Paper Trading • AI Alerts</p>
</div>
""", unsafe_allow_html=True)

# Feature pills
st.markdown("""
<div class="feature-row">
  <span class="feature-pill">📈 Live Prices</span>
  <span class="feature-pill">🔔 Smart Alerts</span>
  <span class="feature-pill">🧪 Scenario Engine</span>
  <span class="feature-pill">💼 Paper Trading</span>
  <span class="feature-pill">⏰ Time Machine</span>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------ tabs
tab_login, tab_register, tab_forgot = st.tabs([
    "🔑  Sign In",
    "✨  Create Account",
    "🔒  Forgot Password",
])

# ===== SIGN IN =====
with tab_login:
    st.markdown("#### Welcome back")
    email_li    = st.text_input("📧 Email",    placeholder="you@example.com",       key="li_email")
    password_li = st.text_input("🔒 Password", placeholder="Your password",           key="li_pass", type="password")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀  Sign In", type="primary", key="btn_login", use_container_width=True):
        if not email_li.strip() or not password_li:
            st.error("❌ Please enter both email and password.")
        else:
            with st.spinner("Signing in..."):
                ok, result = login(email_li.strip().lower(), password_li)
            if ok:
                st.success(f"✅ Welcome back, **{result['full_name']}**!")
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ {result}")

    st.markdown('<div class="auth-divider">New here?</div>', unsafe_allow_html=True)
    st.markdown("👉 Switch to the **Create Account** tab above to register.")

# ===== REGISTER =====
with tab_register:
    st.markdown("#### Create your free account")

    c1, c2 = st.columns(2)
    with c1: fname = st.text_input("👤 First Name", placeholder="Rahul",               key="rg_fname")
    with c2: lname = st.text_input("Last Name",    placeholder="Sharma",              key="rg_lname")

    email_rg    = st.text_input("📧 Email Address", placeholder="you@example.com",   key="rg_email")
    phone_rg    = st.text_input("📱 Phone (optional)", placeholder="+919876543210", key="rg_phone")
    password_rg = st.text_input("🔒 Password",       placeholder="Min 6 characters", key="rg_pass",  type="password")
    confirm_rg  = st.text_input("🔁 Confirm Password", placeholder="Repeat password",key="rg_conf",  type="password")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✨  Create Account", type="primary", key="btn_register", use_container_width=True):
        full_name = f"{fname.strip()} {lname.strip()}".strip()
        errors = []
        if not email_rg.strip():         errors.append("Email is required.")
        if not password_rg:              errors.append("Password is required.")
        elif len(password_rg) < 6:       errors.append("Password must be at least 6 characters.")
        elif password_rg != confirm_rg:  errors.append("Passwords do not match.")
        if not full_name:                errors.append("Please enter your name.")

        if errors:
            for e in errors: st.error(f"❌ {e}")
        else:
            with st.spinner("Creating your account..."):
                ok, msg = register(
                    email=email_rg.strip().lower(),
                    password=password_rg,
                    full_name=full_name,
                    phone=phone_rg.strip(),
                )
            if ok:
                st.success(f"✅ {msg}")
                st.info("👉 Switch to the **Sign In** tab to log in.")
            else:
                st.error(f"❌ {msg}")

    st.caption("🔒 Your password is encrypted and stored securely in Supabase.")

# ===== FORGOT PASSWORD =====
with tab_forgot:
    st.markdown("#### Reset your password")
    st.caption("Enter your email and we’ll send a password reset link.")

    email_fp = st.text_input("📧 Email Address", placeholder="you@example.com", key="fp_email")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📨  Send Reset Link", type="primary", key="btn_forgot", use_container_width=True):
        if not email_fp.strip():
            st.error("❌ Please enter your email address.")
        else:
            with st.spinner("Sending..."):
                ok, msg = reset_password(email_fp.strip().lower())
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

    st.caption("💡 The reset email comes from Supabase. Check your spam folder if not received.")
