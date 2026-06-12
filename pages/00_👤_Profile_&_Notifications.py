"""
Page: User Profile & Notification Settings

Users enter their email and phone number here.
These are stored in st.session_state and used by the Alerts page
to send real email (SMTP via Gmail) and SMS (Twilio) when a price alert fires.

NO real money. NO brokerage. Pure notification layer.
"""
import re
import streamlit as st
from utils.notifications import send_email, send_sms

st.set_page_config(
    page_title="Profile & Notifications",
    page_icon="👤",
    layout="wide",
)

# ------------------------------------------------------------------ helpers

EMAIL_RE  = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$")
PHONE_RE  = re.compile(r"^\+?[1-9]\d{7,14}$")   # E.164 format

def valid_email(s: str) -> bool:
    return bool(EMAIL_RE.match(s.strip()))

def valid_phone(s: str) -> bool:
    cleaned = s.strip().replace(" ", "").replace("-", "")
    return bool(PHONE_RE.match(cleaned))


# ------------------------------------------------------------------ session state defaults

for key, default in [
    ("user_email",         ""),
    ("user_phone",         ""),
    ("notify_email",       True),
    ("notify_sms",         False),
    ("profile_saved",      False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ------------------------------------------------------------------ UI

st.title("👤 Profile & Notification Settings")
st.markdown("""
Configure your contact details so the **🔔 Alerts** page can notify you
via **email** and/or **SMS** the moment a price alert fires.

> 🟡 All details stay in your browser session only — nothing is stored on any server.
> Add your credentials in **Streamlit Secrets** (`SMTP_*` / `TWILIO_*`) to enable live sending.
""")

st.markdown("---")

# ---- Contact details ----
st.subheader("📬 Contact Details")

col1, col2 = st.columns(2)
with col1:
    email_input = st.text_input(
        "📧 Email Address",
        value=st.session_state["user_email"],
        placeholder="you@example.com",
        key="_email_input",
    )
with col2:
    phone_input = st.text_input(
        "📱 Phone Number (E.164 format, e.g. +919876543210)",
        value=st.session_state["user_phone"],
        placeholder="+919876543210",
        key="_phone_input",
    )

# Validate
email_ok = valid_email(email_input) if email_input.strip() else True
phone_ok = valid_phone(phone_input) if phone_input.strip() else True

if email_input.strip() and not email_ok:
    st.warning("⚠️ Invalid email address format.")
if phone_input.strip() and not phone_ok:
    st.warning("⚠️ Invalid phone number. Use E.164 format: +91XXXXXXXXXX")

st.markdown("---")

# ---- Notification channels ----
st.subheader("🔔 Notification Channels")

nc1, nc2 = st.columns(2)
with nc1:
    notify_email = st.toggle(
        "📧 Send Email on Alert",
        value=st.session_state["notify_email"],
        key="_notify_email",
    )
with nc2:
    notify_sms = st.toggle(
        "📱 Send SMS on Alert (Twilio)",
        value=st.session_state["notify_sms"],
        key="_notify_sms",
    )

st.markdown("---")

# ---- Save ----
if st.button("💾 Save Profile", type="primary"):
    if notify_email and not valid_email(email_input):
        st.error("❌ Please enter a valid email address before enabling email notifications.")
    elif notify_sms and not valid_phone(phone_input):
        st.error("❌ Please enter a valid phone number before enabling SMS notifications.")
    else:
        st.session_state["user_email"]    = email_input.strip()
        st.session_state["user_phone"]    = phone_input.strip().replace(" ", "").replace("-", "")
        st.session_state["notify_email"]  = notify_email
        st.session_state["notify_sms"]    = notify_sms
        st.session_state["profile_saved"] = True
        st.success("✅ Profile saved! The Alerts page will now notify you when thresholds are hit.")

# ---- Summary badge ----
if st.session_state["profile_saved"]:
    with st.container(border=True):
        st.markdown("### 📌 Saved Profile")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📧 Email",    st.session_state["user_email"]  or "—")
        c2.metric("📱 Phone",    st.session_state["user_phone"]  or "—")
        c3.metric("Email Alerts",  "✅ On" if st.session_state["notify_email"] else "❌ Off")
        c4.metric("SMS Alerts",    "✅ On" if st.session_state["notify_sms"]   else "❌ Off")

st.markdown("---")

# ---- Test notifications ----
st.subheader("🧪 Test Notifications")
st.caption("Send a test message right now to verify your SMTP / Twilio config.")

t1, t2 = st.columns(2)

with t1:
    st.markdown("**📧 Test Email**")
    if st.button("🚀 Send Test Email"):
        addr = st.session_state.get("user_email", "")
        if not addr:
            st.error("❌ Save a valid email first.")
        else:
            ok, err = send_email(
                to_addr=addr,
                subject="🔔 Nifty50 Tracker — Test Alert",
                body=(
                    "Hello!\n\n"
                    "This is a test message from your Nifty50 Stock Tracker app.\n"
                    "Email notifications are working correctly.\n\n"
                    "Happy trading!"
                ),
            )
            if ok:
                st.success(f"✅ Test email sent to {addr}")
            else:
                st.error(f"❌ Email failed: {err}")
                st.info(
                    "Make sure you have set **SMTP_HOST**, **SMTP_PORT**, "
                    "**SMTP_USER**, **SMTP_PASS**, **SMTP_FROM** in "
                    "`.streamlit/secrets.toml` (local) or Streamlit Cloud Secrets."
                )

with t2:
    st.markdown("**📱 Test SMS**")
    if st.button("🚀 Send Test SMS"):
        phone = st.session_state.get("user_phone", "")
        if not phone:
            st.error("❌ Save a valid phone number first.")
        else:
            ok, err = send_sms(
                to_number=phone,
                body="🔔 Nifty50 Tracker — SMS notifications are working!",
            )
            if ok:
                st.success(f"✅ Test SMS sent to {phone}")
            else:
                st.error(f"❌ SMS failed: {err}")
                st.info(
                    "Make sure you have set **TWILIO_SID**, **TWILIO_TOKEN**, "
                    "**TWILIO_FROM** in `.streamlit/secrets.toml` or Streamlit Cloud Secrets."
                )

st.markdown("---")

# ---- Setup guide ----
with st.expander("ℹ️ How to configure SMTP & Twilio credentials"):
    st.markdown("""
### Step 1 — Create `.streamlit/secrets.toml` (local) or add Streamlit Cloud Secrets

```toml
# Email (Gmail example — use an App Password, NOT your main password)
[smtp]
host     = "smtp.gmail.com"
port     = 587
user     = "youremail@gmail.com"
password = "your_16char_app_password"
from     = "youremail@gmail.com"

# Twilio (get free trial at twilio.com)
[twilio]
sid   = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
token = "your_auth_token"
from  = "+1415XXXXXXX"   # your Twilio number
```

### Step 2 — Gmail App Password
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Create an app password for "Mail"
3. Use that 16-character password above (not your Gmail login password)

### Step 3 — Twilio Free Trial
1. Sign up at [twilio.com](https://www.twilio.com/try-twilio)
2. Get a free phone number
3. Copy your **Account SID** and **Auth Token** from the dashboard
4. Note: free trial can only SMS verified numbers
    """)
