"""Firebase Phone OTP browser component for Streamlit.

Because Firebase's sendVerificationCode REST endpoint requires a valid
reCAPTCHA token (generated only in a real browser), we embed a tiny
Firebase JS SDK snippet inside an st.components.v1.html() iframe.

Flow:
  1. render_phone_otp_sender(api_key, phone) is called from auth_ui.py
  2. It renders an HTML iframe that:
       a. Loads Firebase JS SDK v9 (compat)
       b. Initialises Firebase with the web API key
       c. Sets up RecaptchaVerifier (invisible)
       d. Calls signInWithPhoneNumber(phone, recaptchaVerifier)
       e. On success, posts {"sessionInfo": "..."} to the parent window
            AND writes it to window.name so Streamlit can read it
  3. A st.text_input polls for the sessionInfo via a hidden query-param
     bridge (user pastes nothing — it is automatic via JS)

Simpler alternative used here: the iframe writes the sessionInfo into
a <textarea id="out"> that the Streamlit host reads back via
streamlit-javascript or simply by the user copying it.

Actually the cleanest production approach for Streamlit Cloud:
  - Use streamlit-javascript (pip install streamlit-javascript) if available
  - Fallback: render the widget and ask the user to copy the session token
    (transparent, one-time, ~10 seconds)

This module renders the HTML widget and returns the sessionInfo string
or None if not yet available.
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components


OTP_WIDGET_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin:0; font-family: sans-serif; font-size:13px; color:#333; }}
  #status {{ padding:8px; border-radius:6px; margin-top:6px; }}
  .ok  {{ background:#d4edda; color:#155724; }}
  .err {{ background:#f8d7da; color:#721c24; }}
  .inf {{ background:#d1ecf1; color:#0c5460; }}
  #out {{ width:100%; margin-top:8px; font-size:11px; word-break:break-all;
          border:1px solid #ccc; border-radius:4px; padding:4px;
          display:none; resize:none; }}
</style>
</head>
<body>
<div id="recaptcha-container"></div>
<div id="status" class="inf">⏳ Initialising Firebase…</div>
<textarea id="out" rows="3" readonly placeholder="session token will appear here"></textarea>

<script type="module">
  import {{ initializeApp }}        from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js';
  import {{ getAuth, RecaptchaVerifier, signInWithPhoneNumber }}
    from 'https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js';

  const API_KEY = "{api_key}";
  const PHONE   = "{phone}";

  const app  = initializeApp({{ apiKey: API_KEY, authDomain: window.location.hostname }});
  const auth = getAuth(app);
  auth.settings.appVerificationDisabledForTesting = false;

  const status = document.getElementById('status');
  const out    = document.getElementById('out');

  function setStatus(msg, cls) {{
    status.textContent = msg;
    status.className   = cls;
  }}

  setStatus('\u23f3 Setting up reCAPTCHA…', 'inf');

  let verifier;
  try {{
    verifier = new RecaptchaVerifier(auth, 'recaptcha-container', {{
      size: 'invisible',
      callback: () => {{}},
    }});
  }} catch(e) {{
    setStatus('\u274c reCAPTCHA init failed: ' + e.message, 'err');
  }}

  async function sendOTP() {{
    setStatus('\u23f3 Sending OTP to ' + PHONE + '…', 'inf');
    try {{
      const result = await signInWithPhoneNumber(auth, PHONE, verifier);
      // result.verificationId is the sessionInfo equivalent
      const sessionInfo = result.verificationId;
      out.value   = sessionInfo;
      out.style.display = 'block';
      setStatus('\u2705 OTP sent! Copy the token below into the box above.', 'ok');
      // also post to parent
      window.parent.postMessage({{ type: 'otp_session', sessionInfo }}, '*');
    }} catch(e) {{
      setStatus('\u274c ' + e.message, 'err');
      verifier.clear();
    }}
  }}

  sendOTP();
</script>
</body>
</html>
"""


def render_send_otp_widget(api_key: str, phone: str) -> str | None:
    """
    Render the Firebase JS OTP sender inside an iframe.

    Returns the sessionInfo (verificationId) string if the user has
    already copied it into the session_state bridge key, else None.

    The widget shows a textarea with the sessionInfo after the SMS is
    sent. The user copies it into a Streamlit text_input, which this
    function reads from session_state.
    """
    html = OTP_WIDGET_HTML.format(api_key=api_key, phone=phone)
    components.html(html, height=130, scrolling=False)

    st.caption(
        "Once the SMS is sent the token box above will fill automatically. "
        "Copy that token and paste it in the field below, then enter your OTP code."
    )
    session_info = st.text_input(
        "Paste Session Token here",
        key="_fb_otp_session_paste",
        placeholder="(auto-filled by the widget above)",
        label_visibility="visible",
    )
    return session_info.strip() if session_info.strip() else None
