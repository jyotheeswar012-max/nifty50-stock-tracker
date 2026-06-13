"""
Page: Login / Register / Forgot Password  —  light theme
"""
import streamlit as st
from utils.supabase_auth import register, login, logout, get_current_user, reset_password, supabase_ready
from utils.theme import inject

st.set_page_config(page_title="Sign In — Nifty50 Tracker", page_icon="📈", layout="centered")
inject()

st.markdown("""
<style>
[data-testid="stSidebar"] { display:none !important; }
.login-hero {
  text-align: center;
  padding: 2rem 1rem 1.2rem;
}
.login-hero h1 {
  font-size: 2.4rem;
  font-weight: 900;
  color: #4f46e5 !important;
  margin: 0;
  line-height: 1.1;
}
.login-hero p {
  color: #475569 !important;
  font-size: 1rem;
  margin: 8px 0 0;
  font-weight: 500;
}
.pill-row {
  display: flex; flex-wrap: wrap; justify-content: center;
  gap: 8px; margin: 1rem 0 1.8rem;
}
.feat-pill {
  background: #ede9fe;
  border: 1px solid #c4b5fd;
  border-radius: 20px;
  padding: 5px 16px;
  font-size: 0.82rem;
  font-weight: 700;
  color: #4338ca !important;
}
.guest-link {
  text-align: center;
  margin-bottom: 1.2rem;
}
.guest-link a {
  color: #6366f1 !important;
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
}
.guest-link a:hover { text-decoration: underline; }
.divider-text {
  display: flex; align-items: center; gap: 12px;
  color: #64748b !important;
  font-size: .85rem;
  margin: 1rem 0;
  font-weight: 600;
}
.divider-text::before,.divider-text::after {
  content: ""; flex: 1; border-top: 1px solid #e0eaff;
}
.google-btn {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  background: #ffffff;
  color: #374151 !important;
  border: 1.5px solid #c7d2fe;
  border-radius: 12px;
  padding: 11px 0;
  font-weight: 700;
  font-size: .95rem;
  cursor: pointer;
  width: 100%;
  text-decoration: none;
  transition: box-shadow .2s, border-color .2s;
}
.google-btn:hover { box-shadow: 0 4px 14px rgba(99,102,241,.2); border-color: #6366f1; }
.ui-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 1.4rem 1.6rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 12px rgba(15,23,42,.07);
  margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

user = get_current_user()
if user:
    st.success(f"✅ Signed in as **{user['full_name']}** ({user['email']})", icon="👋")
    c1, c2 = st.columns(2)
    with c1: st.page_link("app.py", label="➡️ Go to Dashboard", icon="📈")
    with c2:
        if st.button("🚧 Sign Out", use_container_width=True):
            logout(); st.rerun()
    st.stop()

st.markdown("""
<div class="login-hero">
  <h1>📈 Nifty50 Tracker</h1>
  <p>NSE India &bull; Real-Time Prices &bull; Paper Trading &bull; AI Alerts</p>
</div>
<div class="pill-row">
  <span class="feat-pill">📈 Live Prices</span>
  <span class="feat-pill">🔔 Smart Alerts</span>
  <span class="feat-pill">🧪 Scenario Engine</span>
  <span class="feat-pill">💼 Paper Portfolio</span>
  <span class="feat-pill">🤖 ML Predictions</span>
  <span class="feat-pill">⏰ Time Machine</span>
</div>
<div class="guest-link">
  <a href="/" target="_self">👁️ Browse as Guest &mdash; no account needed</a>
</div>
""", unsafe_allow_html=True)

if not supabase_ready():
    st.warning("⚠️ Supabase not configured. Login / Register unavailable.", icon="⚙️")
    with st.expander("📖 Setup Guide"):
        st.markdown("""
**1.** Create a free project at [supabase.com](https://supabase.com)  
**2.** Add to `.streamlit/secrets.toml`:
```toml
[supabase]
url      = "https://xxxx.supabase.co"
anon_key = "eyJ..."
```
**3.** Redeploy / restart the app.
        """)

tab_login, tab_reg, tab_forgot = st.tabs(["🔑  Sign In", "✨  Create Account", "🔒  Forgot Password"])

with tab_login:
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown("### Welcome back 👋")
    try:
        supabase_url = st.secrets["supabase"]["url"]
        redirect_uri = st.secrets["google"]["redirect_uri"]
        g_url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={redirect_uri}"
        st.markdown(
            f'<a href="{g_url}" class="google-btn" target="_self">'
            f'<img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="20"/>'
            f'Continue with Google</a>', unsafe_allow_html=True)
        st.markdown('<div class="divider-text">or sign in with email</div>', unsafe_allow_html=True)
    except Exception:
        pass
    email_li = st.text_input("📧 Email", placeholder="you@example.com", key="li_email")
    pass_li  = st.text_input("🔒 Password", placeholder="Your password", key="li_pass", type="password")
    if st.button("🚀  Sign In", type="primary", key="btn_login", use_container_width=True):
        if not email_li.strip() or not pass_li:
            st.error("❌ Please enter both email and password.")
        else:
            with st.spinner("Signing in…"):
                ok, res = login(email_li.strip().lower(), pass_li)
            if ok:
                st.success(f"✅ Welcome back, **{res['full_name']}**!"); st.balloons(); st.rerun()
            else:
                st.error(f"❌ {res}")
    st.markdown("</div>", unsafe_allow_html=True)

with tab_reg:
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown("### Create your free account ✨")
    c1, c2 = st.columns(2)
    with c1: fname = st.text_input("👤 First Name", placeholder="Rahul",  key="rg_fname")
    with c2: lname = st.text_input("Last Name",  placeholder="Sharma", key="rg_lname")
    email_rg = st.text_input("📧 Email",            placeholder="you@example.com",  key="rg_email")
    phone_rg = st.text_input("📱 Phone (optional)", placeholder="+919876543210",    key="rg_phone")
    pass_rg  = st.text_input("🔒 Password",         placeholder="Min 6 characters", key="rg_pass",  type="password")
    conf_rg  = st.text_input("🔁 Confirm Password", placeholder="Repeat password",   key="rg_conf",  type="password")
    if st.button("✨  Create Account", type="primary", key="btn_reg", use_container_width=True):
        full_name = f"{fname.strip()} {lname.strip()}".strip()
        errs = []
        if not email_rg.strip():   errs.append("Email is required.")
        if not pass_rg:            errs.append("Password is required.")
        elif len(pass_rg) < 6:     errs.append("Password must be ≥ 6 characters.")
        elif pass_rg != conf_rg:   errs.append("Passwords do not match.")
        if not full_name:          errs.append("Please enter your name.")
        if errs:
            for e in errs: st.error(f"❌ {e}")
        else:
            with st.spinner("Creating account…"):
                ok, msg = register(email_rg.strip().lower(), pass_rg, full_name, phone_rg.strip())
            if ok: st.success(f"✅ {msg}"); st.info("👉 Switch to **Sign In** to log in.")
            else:  st.error(f"❌ {msg}")
    st.caption("🔒 Passwords are encrypted and stored securely in Supabase.")
    st.markdown("</div>", unsafe_allow_html=True)

with tab_forgot:
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    st.markdown("### Reset your password 🔒")
    st.caption("We'll send a secure reset link to your email.")
    email_fp = st.text_input("📧 Email", placeholder="you@example.com", key="fp_email")
    if st.button("📨  Send Reset Link", type="primary", key="btn_forgot", use_container_width=True):
        if not email_fp.strip():
            st.error("❌ Please enter your email.")
        else:
            with st.spinner("Sending…"):
                ok, msg = reset_password(email_fp.strip().lower())
            if ok: st.success(f"✅ {msg}")
            else:  st.error(f"❌ {msg}")
    st.caption("💡 Check your spam folder if not received within 2 minutes.")
    st.markdown("</div>", unsafe_allow_html=True)
