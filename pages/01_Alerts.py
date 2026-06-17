import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Price Alerts", page_icon="🔔", layout="wide", initial_sidebar_state="collapsed")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    def inject_topbar(user=None): pass

try:
    from utils.supabase_auth import get_current_user, is_guest, login_nudge
except Exception:
    def get_current_user(): return None
    def is_guest(): return True
    def login_nudge(msg=""): st.info("Sign in to save your data.")

try:
    from utils.notifications import send_email, smtp_configured
except Exception:
    def send_email(to, subject, body): return False, "notifications module unavailable"
    def smtp_configured(): return False

user = get_current_user()
try:
    inject_topbar(user=user)
except Exception:
    pass

NIFTY50 = [
    {"symbol":"RELIANCE.NS","name":"Reliance Industries"},
    {"symbol":"HDFCBANK.NS","name":"HDFC Bank"},
    {"symbol":"ICICIBANK.NS","name":"ICICI Bank"},
    {"symbol":"INFY.NS","name":"Infosys"},
    {"symbol":"TCS.NS","name":"TCS"},
    {"symbol":"BHARTIARTL.NS","name":"Bharti Airtel"},
    {"symbol":"ITC.NS","name":"ITC"},
    {"symbol":"KOTAKBANK.NS","name":"Kotak Mahindra Bank"},
    {"symbol":"LT.NS","name":"Larsen & Toubro"},
    {"symbol":"HCLTECH.NS","name":"HCL Technologies"},
    {"symbol":"AXISBANK.NS","name":"Axis Bank"},
    {"symbol":"SBIN.NS","name":"State Bank of India"},
    {"symbol":"BAJFINANCE.NS","name":"Bajaj Finance"},
    {"symbol":"WIPRO.NS","name":"Wipro"},
    {"symbol":"ASIANPAINT.NS","name":"Asian Paints"},
    {"symbol":"MARUTI.NS","name":"Maruti Suzuki"},
    {"symbol":"SUNPHARMA.NS","name":"Sun Pharmaceutical"},
    {"symbol":"TITAN.NS","name":"Titan Company"},
    {"symbol":"ULTRACEMCO.NS","name":"UltraTech Cement"},
    {"symbol":"ONGC.NS","name":"ONGC"},
    {"symbol":"NTPC.NS","name":"NTPC"},
    {"symbol":"POWERGRID.NS","name":"Power Grid Corp"},
    {"symbol":"M&M.NS","name":"Mahindra & Mahindra"},
    {"symbol":"TATAMOTORS.NS","name":"Tata Motors"},
    {"symbol":"TATASTEEL.NS","name":"Tata Steel"},
    {"symbol":"JSWSTEEL.NS","name":"JSW Steel"},
    {"symbol":"HINDALCO.NS","name":"Hindalco Industries"},
    {"symbol":"ADANIENT.NS","name":"Adani Enterprises"},
    {"symbol":"ADANIPORTS.NS","name":"Adani Ports"},
    {"symbol":"BAJAJFINSV.NS","name":"Bajaj Finserv"},
    {"symbol":"BAJAJAUTO.NS","name":"Bajaj Auto"},
    {"symbol":"HEROMOTOCO.NS","name":"Hero MotoCorp"},
    {"symbol":"CIPLA.NS","name":"Cipla"},
    {"symbol":"DRREDDY.NS","name":"Dr. Reddy's Labs"},
    {"symbol":"DIVISLAB.NS","name":"Divi's Laboratories"},
    {"symbol":"EICHERMOT.NS","name":"Eicher Motors"},
    {"symbol":"GRASIM.NS","name":"Grasim Industries"},
    {"symbol":"HDFCLIFE.NS","name":"HDFC Life Insurance"},
    {"symbol":"SBILIFE.NS","name":"SBI Life Insurance"},
    {"symbol":"INDUSINDBK.NS","name":"IndusInd Bank"},
    {"symbol":"TATACONSUM.NS","name":"Tata Consumer Products"},
    {"symbol":"BRITANNIA.NS","name":"Britannia Industries"},
    {"symbol":"NESTLEIND.NS","name":"Nestle India"},
    {"symbol":"HINDUNILVR.NS","name":"Hindustan Unilever"},
    {"symbol":"COALINDIA.NS","name":"Coal India"},
    {"symbol":"BPCL.NS","name":"BPCL"},
    {"symbol":"TECHM.NS","name":"Tech Mahindra"},
    {"symbol":"LTF.NS","name":"L&T Finance"},
    {"symbol":"SHRIRAMFIN.NS","name":"Shriram Finance"},
    {"symbol":"BEL.NS","name":"Bharat Electronics"},
]
N2S = {s["name"]: s["symbol"] for s in NIFTY50}
NAMES = [s["name"] for s in NIFTY50]
IST = pytz.timezone("Asia/Kolkata")


def sf(v, d=0.0):
    try:
        f = float(v)
        return d if (pd.isna(f) or np.isinf(f)) else f
    except Exception:
        return d


def _fmt(value: float) -> str:
    """ASCII-safe price string — avoids locale \\xa0 thousands separator."""
    integer_part, decimal_part = f"{value:.2f}".split(".")
    chars = list(integer_part)
    for i in range(len(chars) - 3, 0, -3):
        chars.insert(i, ",")
    return "".join(chars) + "." + decimal_part


def _send_alert_email(alert: dict, cp: float, user_email: str) -> None:
    """Send a triggered-alert email. Silently logs result to session state."""
    if not smtp_configured():
        return
    # Skip if already emailed for this trigger
    if alert.get("email_sent"):
        return
    target_str = _fmt(alert["target"])
    cp_str     = _fmt(cp)
    ttype      = alert["type"]
    stock      = alert["stock"]
    subject = f"Nifty50 Alert: {stock} {ttype} target Rs.{target_str} hit!"
    body = (
        f"Your price alert has been triggered!\n\n"
        f"Stock   : {stock} ({alert['symbol']})\n"
        f"Trigger : {ttype} Rs.{target_str}\n"
        f"Current : Rs.{cp_str}\n"
        f"Time    : {datetime.now(IST).strftime('%d %b %Y %I:%M:%S %p IST')}\n"
    )
    if alert.get("note"):
        body += f"Note    : {alert['note']}\n"
    body += "\n-- NSE & Nifty 50 Tracker"

    ok, err = send_email(user_email, subject, body)
    alert["email_sent"] = True
    log = st.session_state.setdefault("alert_email_log", [])
    ts  = datetime.now(IST).strftime("%H:%M:%S")
    log.insert(0, f"[{ts}] {stock} -> {'OK' if ok else 'FAILED: ' + err}")


@st.cache_data(ttl=60)
def get_price(sym):
    for period, interval in [("1d", "1m"), ("5d", None)]:
        try:
            kw = dict(period=period, auto_adjust=True)
            if interval:
                kw["interval"] = interval
            h = yf.Ticker(sym).history(**kw)
            if h is not None and not h.empty:
                c = h["Close"]
                if isinstance(c, pd.DataFrame):
                    c = c.iloc[:, 0]
                p = sf(c.iloc[-1])
                if p > 0:
                    return p
        except Exception:
            pass
    return None


for k, v in [("alerts", []), ("alert_history", []), ("alert_email_log", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">🔔</div>
  <div>
    <div class="hero-title">Price Alerts</div>
    <div class="hero-sub">
      <span class='ui-badge badge-live'>Live Monitoring</span>
      &nbsp;&nbsp;Get notified when stocks hit your target price
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if is_guest():
    login_nudge("save your alerts permanently")

# Show SMTP status
if not smtp_configured():
    st.warning("Email notifications are not configured. Add [smtp] to your secrets.toml to receive email alerts.")

# Email recipient — use logged-in user's email or let them enter one
alert_email = ""
if user and getattr(user, "email", None):
    alert_email = user.email
    st.caption(f"Alert emails will be sent to **{alert_email}**")
else:
    alert_email = st.text_input("Alert email address", placeholder="you@example.com", key="alert_email_input")

tab_set, tab_active, tab_hist = st.tabs(["Set Alert", "Active Alerts", "Alert History"])

with tab_set:
    st.markdown("<p class='sec-label'>Create New Alert</p>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        sel_name = st.selectbox("Stock", NAMES, key="al_name")
    with c2:
        al_type = st.selectbox("Trigger", ["Above", "Below", "Change % (+/-)"], key="al_type")
    with c3:
        al_val = st.number_input("Target", min_value=0.0, value=0.0, step=0.5, key="al_val")
    with c4:
        lp = get_price(N2S[sel_name])
        if lp:
            st.metric("Live Price", f"Rs.{_fmt(lp)}")
        else:
            st.warning("Price unavailable")
    al_note = st.text_input("Note (optional)", max_chars=80, key="al_note")
    if st.button("Add Alert", type="primary", key="btn_add_alert"):
        if al_val <= 0:
            st.error("Target must be > 0")
        else:
            st.session_state.alerts.append({
                "stock": sel_name,
                "symbol": N2S[sel_name],
                "type": al_type,
                "target": al_val,
                "note": al_note,
                "created": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
                "status": "Active",
                "current_price": lp or 0,
                "ref_price": lp or 0,
                "email_sent": False,
            })
            st.success(f"Alert set: {sel_name} {al_type} Rs.{_fmt(al_val)}")
            st.rerun()

with tab_active:
    alerts = st.session_state.alerts
    active = [a for a in alerts if a["status"] == "Active"]
    if not active:
        st.info("No active alerts. Create one in the 'Set Alert' tab.")
    else:
        st.markdown(f"<p class='sec-label'>{len(active)} Active Alert(s)</p>", unsafe_allow_html=True)
        triggered = []
        for i, a in enumerate(active):
            cp = get_price(a["symbol"]) or a["current_price"]
            a["current_price"] = cp
            trig = False
            if a["type"] == "Above" and cp >= a["target"]:
                trig = True
            elif a["type"] == "Below" and cp <= a["target"]:
                trig = True
            elif a["type"] == "Change % (+/-)":
                ref = a.get("ref_price") or cp
                if ref and ref != 0 and abs((cp - ref) / ref * 100) >= a["target"]:
                    trig = True

            # Send email the first time the alert triggers
            if trig and alert_email and not a.get("email_sent"):
                _send_alert_email(a, cp, alert_email)

            diff = cp - a["target"]
            pct  = diff / a["target"] * 100 if a["target"] else 0
            status = "TRIGGERED" if trig else "Watching"
            bg     = "#fff1f2" if trig else "#f0fdf4"
            border = "#fda4af" if trig else "#86efac"
            note_html = f"<br><small>{a['note']}</small>" if a.get("note") else ""
            email_badge = " | Email sent" if a.get("email_sent") else ""
            st.markdown(
                f"<div style='background:{bg};border-radius:10px;padding:.8rem 1.2rem;"
                f"margin-bottom:.5rem;border:1px solid {border};'>"
                f"<b>{a['stock']}</b> &nbsp;-&nbsp; {a['type']} <b>Rs.{_fmt(a['target'])}</b>"
                f" &nbsp;|&nbsp; Live: <b>Rs.{_fmt(cp)}</b>"
                f" &nbsp;|&nbsp; Gap: {diff:+.2f} ({pct:+.2f}%)"
                f" &nbsp;|&nbsp; <b>{status}</b>{email_badge}{note_html}</div>",
                unsafe_allow_html=True,
            )
            if trig:
                triggered.append(i)

        # Show email log
        email_log = st.session_state.get("alert_email_log", [])
        if email_log:
            with st.expander("Email log"):
                for entry in email_log[:10]:
                    st.text(entry)

        if triggered:
            if st.button("Mark Triggered as Done", key="btn_mark_done"):
                for i in triggered:
                    st.session_state.alerts[i]["status"] = "Triggered"
                    st.session_state.alert_history.append(st.session_state.alerts[i])
                st.session_state.alerts = [a for a in st.session_state.alerts if a["status"] == "Active"]
                st.rerun()
        if st.button("Clear All Alerts", key="btn_clear_alerts"):
            st.session_state.alerts = []
            st.rerun()

with tab_hist:
    hist = st.session_state.alert_history
    if not hist:
        st.info("No alert history yet.")
    else:
        st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
        if st.button("Clear History", key="btn_clear_hist"):
            st.session_state.alert_history = []
            st.rerun()
