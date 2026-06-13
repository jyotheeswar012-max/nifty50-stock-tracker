"""
Page: Profile & Notifications — requires login (hard gate).
"""
import re
import streamlit as st
from utils.supabase_auth import require_login, logout, update_profile

st.set_page_config(page_title="Profile & Notifications", page_icon="👤", layout="wide")
user = require_login()

# Safe import of notifications helpers
try:
    from utils.notifications import send_email, send_sms, smtp_configured, twilio_configured
except Exception:
    def smtp_configured():          return False
    def twilio_configured():        return False
    def send_email(*a, **k):        return False, "Notifications not configured"
    def send_sms(*a, **k):          return False, "Notifications not configured"

EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.]+$")

for key, default in [
    ("user_email",   user.get("email", "")),
    ("user_phone",   user.get("phone", "")),
    ("notify_email", True),
    ("notify_sms",   False),
    ("app_theme",    "dark"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─ Theme CSS ───────────────────────────────────────────────────────────────
if st.session_state["app_theme"] == "light":
    st.markdown("""
    <style>
    .stApp { background:#f5f5f5 !important; color:#212121 !important; }
    [data-testid="stSidebar"] { background:#ffffff !important; }
    .stMetric label { color:#616161 !important; }
    </style>
    """, unsafe_allow_html=True)

# ─ Header ───────────────────────────────────────────────────────────────
col_h, col_theme, col_out = st.columns([4, 2, 1])
with col_h:
    st.title("👤 Profile & Notification Settings")
    st.caption(f"Signed in as **{user['full_name']}** ({user['email']})")
with col_theme:
    st.markdown("<br>", unsafe_allow_html=True)
    theme_choice = st.radio(
        "🎨 Theme",
        ["🌙 Dark", "☀️ Light"],
        horizontal=True,
        index=0 if st.session_state["app_theme"] == "dark" else 1,
    )
    new_theme = "dark" if theme_choice == "🌙 Dark" else "light"
    if new_theme != st.session_state["app_theme"]:
        st.session_state["app_theme"] = new_theme
        st.rerun()
with col_out:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚧 Sign Out", use_container_width=True):
        logout()
        st.rerun()

st.markdown("---")

# ─ Service status ─────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    if smtp_configured():
        st.success("✅ Email service active")
    else:
        st.error("❌ Email not configured")
with c2:
    if twilio_configured():
        st.success("✅ SMS service active")
    else:
        st.warning("⚠️ SMS not configured")

st.markdown("---")

# ─ Profile update ─────────────────────────────────────────────────────────────
st.subheader("📝 Update Profile")
p1, p2 = st.columns(2)
with p1: new_name  = st.text_input("👤 Full Name",    value=user.get("full_name", ""))
with p2: new_phone = st.text_input("📱 Phone Number", value=user.get("phone", ""),
                                    placeholder="+919876543210")
if st.button("💾 Update Profile", type="primary"):
    ok, msg = update_profile(full_name=new_name, phone=new_phone)
    if ok: st.success(f"✅ {msg}")
    else:  st.error(f"❌ {msg}")

st.markdown("---")

# ─ Notification settings ───────────────────────────────────────────────────────
st.subheader("📬 Alert Delivery")
st.caption("Where should we send your price alerts?")
nc1, nc2 = st.columns(2)
with nc1:
    email_input = st.text_input(
        "📧 Notification Email",
        value=st.session_state["user_email"],
        placeholder="you@example.com",
    )
with nc2:
    phone_input = st.text_input(
        "📱 Notification Phone",
        value=st.session_state["user_phone"],
        placeholder="+919876543210",
        disabled=not twilio_configured(),
    )
t1, t2 = st.columns(2)
with t1:
    notify_email = st.toggle(
        "📧 Email me on alert",
        value=st.session_state["notify_email"],
        disabled=not smtp_configured(),
    )
with t2:
    notify_sms = st.toggle(
        "📱 SMS me on alert",
        value=st.session_state["notify_sms"],
        disabled=not twilio_configured(),
    )
if st.button("💾 Save Notification Settings"):
    st.session_state["user_email"]   = email_input.strip()
    st.session_state["user_phone"]   = phone_input.strip()
    st.session_state["notify_email"] = notify_email
    st.session_state["notify_sms"]   = notify_sms
    st.success("✅ Saved!")

st.markdown("---")

# ─ Test sends ───────────────────────────────────────────────────────────────
st.subheader("🧪 Test Notifications")
tb1, tb2 = st.columns(2)
with tb1:
    if not smtp_configured():
        st.info("ℹ️ Email service not active. Add SMTP secrets to enable.")
    else:
        if st.button("🚀 Send Test Email"):
            addr = st.session_state.get("user_email", "").strip()
            if not addr:
                st.error("❌ Save an email address first.")
            else:
                with st.spinner("Sending..."):
                    ok, err = send_email(addr, "🔔 Nifty50 Tracker — Test Alert",
                                         "Email notifications are working!")
                if ok: st.success(f"✅ Sent to {addr}")
                else:  st.error(f"❌ {err}")
with tb2:
    if not twilio_configured():
        st.info("ℹ️ SMS service not active. Add Twilio secrets to enable.")
    else:
        if st.button("🚀 Send Test SMS"):
            phone = st.session_state.get("user_phone", "").strip()
            if not phone:
                st.error("❌ Save a phone number first.")
            else:
                with st.spinner("Sending..."):
                    ok, err = send_sms(phone, "🔔 Nifty50 Tracker — SMS test working!")
                if ok: st.success(f"✅ Sent to {phone}")
                else:  st.error(f"❌ {err}")
