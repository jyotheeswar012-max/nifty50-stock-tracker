"""
Page: Profile & Notification Settings
Option B — Shared sender. Users enter destination email + phone.
Gated behind require_login().
"""
import re
import streamlit as st
from utils.supabase_auth import require_login, logout, update_profile
from utils.notifications import send_email, send_sms, smtp_configured, twilio_configured

st.set_page_config(page_title="Profile & Notifications", page_icon="👤", layout="wide")

user = require_login()

EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.]+$")
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")

def valid_email(s): return bool(EMAIL_RE.match(s.strip()))
def valid_phone(s): return bool(PHONE_RE.match(s.strip().replace(" ","").replace("-","")))

for key, default in [
    ("user_email",    user.get("email", "")),
    ("user_phone",    user.get("phone", "")),
    ("notify_email",  True),
    ("notify_sms",    False),
    ("profile_saved", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---- header ----
col_h, col_out = st.columns([5, 1])
with col_h:
    st.title("👤 Profile & Notification Settings")
    st.caption(f"Signed in as **{user['full_name']}** ({user['email']})")
with col_out:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Sign Out", use_container_width=True):
        logout()
        st.rerun()

st.markdown("---")

# ---- service status ----
c1, c2 = st.columns(2)
with c1:
    st.success("✅ Email service active") if smtp_configured() else st.error("❌ Email not configured")
with c2:
    st.success("✅ SMS service active") if twilio_configured() else st.warning("⚠️ SMS not configured")

st.markdown("---")

# ---- profile update ----
st.subheader("📝 Update Profile")
p1, p2 = st.columns(2)
with p1:
    new_name  = st.text_input("👤 Full Name",    value=user.get("full_name", ""))
with p2:
    new_phone = st.text_input("📱 Phone Number", value=user.get("phone", ""), placeholder="+919876543210")

if st.button("💾 Update Profile", type="primary"):
    ok, msg = update_profile(full_name=new_name, phone=new_phone)
    st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")

st.markdown("---")

# ---- notification contact ----
st.subheader("📬 Alert Delivery")
st.caption("Where should we send your price alerts?")

nc1, nc2 = st.columns(2)
with nc1:
    email_input = st.text_input("📧 Notification Email",
        value=st.session_state["user_email"], placeholder="you@example.com")
with nc2:
    phone_input = st.text_input("📱 Notification Phone",
        value=st.session_state["user_phone"], placeholder="+919876543210",
        disabled=not twilio_configured())

t1, t2 = st.columns(2)
with t1:
    notify_email = st.toggle("📧 Email me on alert",
        value=st.session_state["notify_email"], disabled=not smtp_configured())
with t2:
    notify_sms = st.toggle("📱 SMS me on alert",
        value=st.session_state["notify_sms"],   disabled=not twilio_configured())

if st.button("💾 Save Notification Settings"):
    st.session_state["user_email"]    = email_input.strip()
    st.session_state["user_phone"]    = phone_input.strip().replace(" ","").replace("-","")
    st.session_state["notify_email"]  = notify_email
    st.session_state["notify_sms"]    = notify_sms
    st.session_state["profile_saved"] = True
    st.success("✅ Notification settings saved!")

st.markdown("---")

# ---- test sends ----
st.subheader("🧪 Test Notifications")
tb1, tb2 = st.columns(2)

with tb1:
    if not smtp_configured():
        st.info("ℹ️ Email service not active.")
    elif st.button("🚀 Send Test Email"):
        addr = st.session_state.get("user_email", "")
        if not addr: st.error("❌ Save an email address first.")
        else:
            with st.spinner("Sending..."):
                ok, err = send_email(addr, "🔔 Nifty50 Tracker — Test Alert",
                    "This is a test. Email notifications are working!")
            st.success(f"✅ Sent to {addr}") if ok else st.error(f"❌ {err}")

with tb2:
    if not twilio_configured():
        st.info("ℹ️ SMS service not active.")
    elif st.button("🚀 Send Test SMS"):
        phone = st.session_state.get("user_phone", "")
        if not phone: st.error("❌ Save a phone number first.")
        else:
            with st.spinner("Sending..."):
                ok, err = send_sms(phone, "🔔 Nifty50 Tracker — SMS test working!")
            st.success(f"✅ Sent to {phone}") if ok else st.error(f"❌ {err}")
