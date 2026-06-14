"""
Login page — plain filename for clean URL /Login
"""
import re
import streamlit as st

st.set_page_config(page_title="Login — NSE Tracker", page_icon="🔐", layout="centered")

try:
    from utils.theme import inject
    inject()
except Exception:
    pass

try:
    from utils.supabase_auth import login, signup, get_current_user, logout
except Exception:
    def login(e, p): return None, "Auth not configured"
    def signup(e, p, n): return None, "Auth not configured"
    def get_current_user(): return None
    def logout(): pass

user = get_current_user()
if user:
    st.success(f"✅ Already signed in as **{user['full_name']}**")
    if st.button("🔙 Go to Dashboard"):
        st.switch_page("app.py")
    if st.button("🚧 Sign Out"):
        logout(); st.rerun()
    st.stop()

st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem;">
  <div style="font-size:3rem;">🔐</div>
  <h1 style="color:#0f172a;font-weight:900;margin:.5rem 0 .2rem;">NSE Tracker</h1>
  <p style="color:#475569;font-size:.95rem;">Sign in to save alerts, watchlist &amp; portfolio</p>
</div>
""", unsafe_allow_html=True)

tab_login, tab_signup = st.tabs(["🔐  Sign In", "👤  Create Account"])

EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.]+$")

with tab_login:
    with st.form("login_form"):
        email = st.text_input("📧 Email", placeholder="you@example.com")
        password = st.text_input("🔒 Password", type="password")
        submitted = st.form_submit_button("🔐 Sign In", use_container_width=True, type="primary")
    if submitted:
        if not email or not password:
            st.error("❌ Please fill in all fields.")
        elif not EMAIL_RE.match(email):
            st.error("❌ Invalid email address.")
        else:
            with st.spinner("Signing in…"):
                user_obj, err = login(email.strip(), password)
            if user_obj:
                st.success(f"✅ Welcome back, {user_obj.get('full_name', email)}!")
                st.rerun()
            else:
                st.error(f"❌ {err}")

with tab_signup:
    with st.form("signup_form"):
        s_name  = st.text_input("👤 Full Name", placeholder="Your Name")
        s_email = st.text_input("📧 Email", placeholder="you@example.com", key="su_email")
        s_pass  = st.text_input("🔒 Password", type="password", key="su_pass")
        s_pass2 = st.text_input("🔒 Confirm Password", type="password", key="su_pass2")
        s_sub   = st.form_submit_button("➕ Create Account", use_container_width=True, type="primary")
    if s_sub:
        if not all([s_name, s_email, s_pass, s_pass2]):
            st.error("❌ Please fill in all fields.")
        elif not EMAIL_RE.match(s_email):
            st.error("❌ Invalid email address.")
        elif s_pass != s_pass2:
            st.error("❌ Passwords do not match.")
        elif len(s_pass) < 6:
            st.error("❌ Password must be at least 6 characters.")
        else:
            with st.spinner("Creating account…"):
                user_obj, err = signup(s_email.strip(), s_pass, s_name.strip())
            if user_obj:
                st.success("✅ Account created! Please check your email to verify, then sign in.")
            else:
                st.error(f"❌ {err}")

st.markdown("<br>",unsafe_allow_html=True)
st.caption("🔒 Your credentials are secured via Supabase Auth. We never store plain-text passwords.")
