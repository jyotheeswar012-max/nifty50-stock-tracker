"""
Profile & Notifications — plain filename for clean URL /Profile
"""
import re
import streamlit as st

st.set_page_config(page_title="Profile & Notifications", page_icon="👤", layout="wide")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    pass

try:
    from utils.supabase_auth import require_login, logout, update_profile
except Exception:
    def require_login():
        st.error("❌ Auth not configured."); st.stop()
    def logout(): pass
    def update_profile(**kw): return False, "Not configured"

user = require_login()

try:
    inject_topbar(user=user)
except Exception:
    pass

try:
    from utils.notifications import send_email, send_sms, smtp_configured, twilio_configured
except Exception:
    def smtp_configured():   return False
    def twilio_configured(): return False
    def send_email(*a, **k): return False, "Not configured"
    def send_sms(*a, **k):   return False, "Not configured"

EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.]+$")
for k, v in [("user_email", user.get("email","")), ("user_phone", user.get("phone","")),
             ("notify_email", True), ("notify_sms", False)]:
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""
<div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem;">
  <div style="width:56px;height:56px;border-radius:50%;
              background:linear-gradient(135deg,#6366f1,#8b5cf6);
              display:flex;align-items:center;justify-content:center;
              font-size:1.6rem;color:#fff;">
    👤
  </div>
  <div>
    <div class="ui-page-title" style="font-size:1.7rem;">Profile &amp; Notifications</div>
    <div class="ui-caption">Manage your account and alert preferences</div>
  </div>
</div>
""", unsafe_allow_html=True)

col_info, col_out = st.columns([8, 1])
with col_info:
    st.markdown(f"<span class='ui-badge badge-nse'>👤 {user['full_name']}</span> <span style='color:#6b7280;font-size:.9rem;margin-left:.5rem;'>{user['email']}</span>", unsafe_allow_html=True)
with col_out:
    if st.button("🚧 Sign Out", use_container_width=True):
        logout(); st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    if smtp_configured(): st.success("✅ Email service is active", icon="📧")
    else: st.error("❌ Email not configured", icon="📧")
with c2:
    if twilio_configured(): st.success("✅ SMS service is active", icon="📱")
    else: st.warning("⚠️ SMS not configured", icon="📱")

st.markdown("<br>", unsafe_allow_html=True)
tab_profile, tab_notif, tab_test = st.tabs(["📝  Update Profile", "🔔  Alert Delivery", "🧪  Test Notifications"])

with tab_profile:
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    with p1: new_name  = st.text_input("👤 Full Name",    value=user.get("full_name",""), key="pf_name")
    with p2: new_phone = st.text_input("📱 Phone Number", value=user.get("phone",""),     key="pf_phone", placeholder="+919876543210")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Save Profile", type="primary", key="btn_save_profile"):
        ok, msg = update_profile(full_name=new_name, phone=new_phone)
        if ok: st.success(f"✅ {msg}")
        else:  st.error(f"❌ {msg}")
    st.markdown("</div>", unsafe_allow_html=True)

with tab_notif:
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    nc1, nc2 = st.columns(2)
    with nc1: email_input = st.text_input("📧 Notification Email", value=st.session_state["user_email"], key="notif_email")
    with nc2: phone_input = st.text_input("📱 Notification Phone", value=st.session_state["user_phone"], key="notif_phone", disabled=not twilio_configured())
    t1, t2 = st.columns(2)
    with t1: notify_email = st.toggle("📧 Email alerts", value=st.session_state["notify_email"], disabled=not smtp_configured(), key="tog_email")
    with t2: notify_sms   = st.toggle("📱 SMS alerts",   value=st.session_state["notify_sms"],   disabled=not twilio_configured(), key="tog_sms")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Save Notification Settings", type="primary", key="btn_save_notif"):
        st.session_state["user_email"]   = email_input.strip()
        st.session_state["user_phone"]   = phone_input.strip()
        st.session_state["notify_email"] = notify_email
        st.session_state["notify_sms"]   = notify_sms
        st.success("✅ Notification settings saved!")
    st.markdown("</div>", unsafe_allow_html=True)

with tab_test:
    st.markdown("<div class='ui-card'>", unsafe_allow_html=True)
    tb1, tb2 = st.columns(2)
    with tb1:
        if not smtp_configured(): st.info("ℹ️ Email service not active.", icon="📧")
        else:
            if st.button("🚀 Send Test Email", use_container_width=True):
                addr = st.session_state.get("user_email","").strip()
                if not addr: st.error("❌ Save an email address first.")
                else:
                    with st.spinner("Sending…"):
                        ok, err = send_email(addr, "🔔 Nifty50 — Test Alert", "Email notifications are working! 🎉")
                    if ok: st.success(f"✅ Sent to {addr}")
                    else:  st.error(f"❌ {err}")
    with tb2:
        if not twilio_configured(): st.info("ℹ️ SMS service not active.", icon="📱")
        else:
            if st.button("🚀 Send Test SMS", use_container_width=True):
                phone = st.session_state.get("user_phone","").strip()
                if not phone: st.error("❌ Save a phone number first.")
                else:
                    with st.spinner("Sending…"):
                        ok, err = send_sms(phone, "🔔 Nifty50 — SMS test working! 🎉")
                    if ok: st.success(f"✅ Sent to {phone}")
                    else:  st.error(f"❌ {err}")
    st.markdown("</div>", unsafe_allow_html=True)
