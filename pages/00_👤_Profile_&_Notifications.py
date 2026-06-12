"""
Page: Profile & Notification Settings

Option B — Shared sender.
Users enter ONLY their destination email and/or phone number.
The app owner's Gmail / Twilio credentials live in Streamlit Secrets.
No user ever needs to configure SMTP or Twilio themselves.
"""
import re
import streamlit as st
from utils.notifications import (
    send_email, send_sms,
    smtp_configured, twilio_configured,
)

st.set_page_config(
    page_title="Profile & Notifications",
    page_icon="👤",
    layout="wide",
)

# ------------------------------------------------------------------ regex
EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.]+$")
PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")

def valid_email(s: str) -> bool:
    return bool(EMAIL_RE.match(s.strip()))

def valid_phone(s: str) -> bool:
    return bool(PHONE_RE.match(s.strip().replace(" ", "").replace("-", "")))


# ------------------------------------------------------------------ session defaults
for key, default in [
    ("user_email",    ""),
    ("user_phone",    ""),
    ("notify_email",  True),
    ("notify_sms",    False),
    ("profile_saved", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ------------------------------------------------------------------ page
st.title("👤 Profile & Notification Settings")
st.markdown("""
Enter your **email address** and/or **phone number** below.
When a price alert fires on the 🔔 Alerts page, the app will instantly
notify you — no account signup or API keys needed on your end.
""")

# ---- service status banners (visible to all users) ----
col_s1, col_s2 = st.columns(2)
with col_s1:
    if smtp_configured():
        st.success("✅ Email service is active")
    else:
        st.error("❌ Email service not configured (contact app owner)")
with col_s2:
    if twilio_configured():
        st.success("✅ SMS service is active")
    else:
        st.warning("⚠️ SMS service not configured — email-only mode")

st.markdown("---")

# ---- contact form ----
st.subheader("📬 Your Contact Details")
st.caption("These are stored in your browser session only — never on any server.")

c1, c2 = st.columns(2)
with c1:
    email_input = st.text_input(
        "📧 Your Email Address",
        value=st.session_state["user_email"],
        placeholder="you@example.com",
    )
with c2:
    phone_input = st.text_input(
        "📱 Your Phone Number",
        value=st.session_state["user_phone"],
        placeholder="+919876543210  (include country code)",
        disabled=not twilio_configured(),
        help="SMS requires Twilio to be set up by the app owner.",
    )

# inline validation
email_ok = valid_email(email_input) if email_input.strip() else True
phone_ok = valid_phone(phone_input.strip().replace(" ","").replace("-","")) if phone_input.strip() else True

if email_input.strip() and not email_ok:
    st.warning("⚠️ Invalid email format.")
if phone_input.strip() and not phone_ok:
    st.warning("⚠️ Use E.164 format: +91XXXXXXXXXX")

st.markdown("---")

# ---- notification channel toggles ----
st.subheader("🔔 Alert Channels")
nt1, nt2 = st.columns(2)
with nt1:
    notify_email = st.toggle(
        "📧 Email me when an alert fires",
        value=st.session_state["notify_email"],
        disabled=not smtp_configured(),
    )
with nt2:
    notify_sms = st.toggle(
        "📱 SMS me when an alert fires",
        value=st.session_state["notify_sms"],
        disabled=not twilio_configured(),
    )

st.markdown("---")

# ---- save ----
if st.button("💾 Save", type="primary"):
    errors = []
    if notify_email and not email_input.strip():
        errors.append("Enter an email address to enable email alerts.")
    elif notify_email and not valid_email(email_input):
        errors.append("Email address format is invalid.")
    if notify_sms and not phone_input.strip():
        errors.append("Enter a phone number to enable SMS alerts.")
    elif notify_sms and not valid_phone(phone_input.strip().replace(" ","").replace("-","")):
        errors.append("Phone number must be in E.164 format (+91XXXXXXXXXX).")

    if errors:
        for e in errors:
            st.error(f"❌ {e}")
    else:
        st.session_state["user_email"]   = email_input.strip()
        st.session_state["user_phone"]   = phone_input.strip().replace(" ","").replace("-","")
        st.session_state["notify_email"] = notify_email
        st.session_state["notify_sms"]   = notify_sms
        st.session_state["profile_saved"]= True
        st.success("✅ Saved! You'll be notified when your price alerts trigger.")
        st.balloons()

# saved profile summary
if st.session_state["profile_saved"]:
    with st.container(border=True):
        st.markdown("#### 📌 Active Notification Profile")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("📧 Email",       st.session_state["user_email"] or "—")
        r2.metric("📱 Phone",       st.session_state["user_phone"] or "—")
        r3.metric("Email Alerts", "✅ On" if st.session_state["notify_email"] else "❌ Off")
        r4.metric("SMS Alerts",   "✅ On" if st.session_state["notify_sms"]   else "❌ Off")

st.markdown("---")

# ---- test buttons ----
st.subheader("🧪 Send a Test Notification")
st.caption("Verify everything is working before relying on live alerts.")

tb1, tb2 = st.columns(2)

with tb1:
    st.markdown("**📧 Test Email**")
    if not smtp_configured():
        st.info("ℹ️ Email service not active.")
    elif st.button("🚀 Send Test Email"):
        addr = st.session_state.get("user_email", "")
        if not addr:
            st.error("❌ Save a valid email address first.")
        else:
            with st.spinner("Sending…"):
                ok, err = send_email(
                    to_addr=addr,
                    subject="🔔 Nifty50 Tracker — Test Alert",
                    body=(
                        "Hello!\n\n"
                        "This is a test message from your Nifty50 Stock Tracker app.\n"
                        "Email notifications are working correctly.\n\n"
                        "You will receive alerts like this one whenever a price "
                        "threshold you set on the 🔔 Alerts page is triggered.\n\n"
                        "Happy trading! 📊"
                    ),
                )
            if ok:
                st.success(f"✅ Test email sent to **{addr}**")
            else:
                st.error(f"❌ Failed: {err}")

with tb2:
    st.markdown("**📱 Test SMS**")
    if not twilio_configured():
        st.info("ℹ️ SMS service not active.")
    elif st.button("🚀 Send Test SMS"):
        phone = st.session_state.get("user_phone", "")
        if not phone:
            st.error("❌ Save a valid phone number first.")
        else:
            with st.spinner("Sending…"):
                ok, err = send_sms(
                    to_number=phone,
                    body="🔔 Nifty50 Tracker — SMS alerts are working! You'll get a message here when your price alerts fire.",
                )
            if ok:
                st.success(f"✅ Test SMS sent to **{phone}**")
            else:
                st.error(f"❌ Failed: {err}")

st.markdown("---")

# ---- how it works explainer ----
with st.expander("ℹ️ How does this work?"):
    st.markdown("""
**You only need to enter your email / phone. That's it.**

The app has a shared Gmail account and Twilio number configured by the app owner.
When your price alert fires on the 🔔 Alerts page, the app automatically:
1. Sends an email **from** the app's Gmail **to** your email address
2. Sends an SMS **from** the app's Twilio number **to** your phone

Your contact details are stored **only in your browser session** and are never
saved to a database or shared with anyone.

> If the email/SMS service shows as inactive, the app owner needs to configure
> the SMTP and Twilio credentials in Streamlit Secrets.
    """)
