import streamlit as st
import pandas as pd
from datetime import date, datetime
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Market Calendar", page_icon="📅", layout="wide")

try:
    from utils.theme import inject, inject_topbar
    inject()
except Exception:
    pass

try:
    from utils.supabase_auth import get_current_user
except Exception:
    def get_current_user(): return None

user = get_current_user()
try:
    inject_topbar(user=user)
except Exception:
    pass

st.markdown("""
<div class="hero-banner">
  <div class="hero-icon">📅</div>
  <div>
    <div class="hero-title">Market Calendar</div>
    <div class="hero-sub"><span class="ui-badge badge-nse">NSE 2026</span>&nbsp; Holidays, RBI MPC dates &amp; key events</div>
  </div>
</div>
""", unsafe_allow_html=True)

NSE_HOLIDAYS_2026 = [
    {"Date":"26 Jan 2026","Day":"Monday","Holiday":"Republic Day"},
    {"Date":"19 Feb 2026","Day":"Thursday","Holiday":"Chhatrapati Shivaji Maharaj Jayanti"},
    {"Date":"20 Mar 2026","Day":"Friday","Holiday":"Good Friday"},
    {"Date":"30 Mar 2026","Day":"Monday","Holiday":"Id-Ul-Fitr (Ramzan Id)"},
    {"Date":"14 Apr 2026","Day":"Tuesday","Holiday":"Dr. Baba Saheb Ambedkar Jayanti"},
    {"Date":"01 May 2026","Day":"Friday","Holiday":"Maharashtra Day"},
    {"Date":"22 May 2026","Day":"Friday","Holiday":"Buddha Pournima"},
    {"Date":"06 Jul 2026","Day":"Monday","Holiday":"Muharram"},
    {"Date":"15 Aug 2026","Day":"Saturday","Holiday":"Independence Day"},
    {"Date":"02 Oct 2026","Day":"Friday","Holiday":"Mahatma Gandhi Jayanti"},
    {"Date":"13 Oct 2026","Day":"Tuesday","Holiday":"Dussehra"},
    {"Date":"20 Oct 2026","Day":"Tuesday","Holiday":"Diwali — Laxmi Pujan (Muhurat Trading)"},
    {"Date":"21 Oct 2026","Day":"Wednesday","Holiday":"Diwali — Balipratipada"},
    {"Date":"02 Nov 2026","Day":"Monday","Holiday":"Guru Nanak Jayanti"},
    {"Date":"25 Dec 2026","Day":"Friday","Holiday":"Christmas"},
]

RBI_MPC_2026 = [
    {"Meeting":"MPC #1","Dates":"05–07 Feb 2026","Decision":"Rate Cut 25bps → 6.25%","Status":"✅ Done"},
    {"Meeting":"MPC #2","Dates":"07–09 Apr 2026","Decision":"Rate Cut 25bps → 6.00%","Status":"✅ Done"},
    {"Meeting":"MPC #3","Dates":"04–06 Jun 2026","Decision":"Rate Cut 25bps → 5.75%","Status":"✅ Done"},
    {"Meeting":"MPC #4","Dates":"05–07 Aug 2026","Decision":"Awaited","Status":"🔜 Upcoming"},
    {"Meeting":"MPC #5","Dates":"29 Sep–01 Oct 2026","Decision":"Awaited","Status":"🔜 Upcoming"},
    {"Meeting":"MPC #6","Dates":"02–04 Dec 2026","Decision":"Awaited","Status":"🔜 Upcoming"},
]

KEY_EVENTS_2026 = [
    {"Date":"01 Feb 2026","Event":"Union Budget 2026-27","Type":"Budget","Impact":"🔴 Very High"},
    {"Date":"Apr–May 2026","Event":"Q4 FY26 Earnings Season","Type":"Earnings","Impact":"🔴 High"},
    {"Date":"Jun 2026","Event":"US Fed FOMC Meeting","Type":"Global","Impact":"🟡 Medium"},
    {"Date":"20 Oct 2026","Event":"Diwali Muhurat Trading","Type":"Special","Impact":"🟢 Positive"},
    {"Date":"Oct–Nov 2026","Event":"Q2 FY27 Earnings Season","Type":"Earnings","Impact":"🔴 High"},
    {"Date":"Dec 2026","Event":"US Fed FOMC Meeting","Type":"Global","Impact":"🟡 Medium"},
]

today = date.today()
next_holiday = next((h for h in NSE_HOLIDAYS_2026 if datetime.strptime(h["Date"],"%d %b %Y").date() >= today), None)
if next_holiday:
    st.info(f"🗓️ **Next NSE Holiday:** {next_holiday['Date']} — {next_holiday['Holiday']} ({next_holiday['Day']})")

next_mpc = next((m for m in RBI_MPC_2026 if m["Status"] == "🔜 Upcoming"), None)
if next_mpc:
    st.warning(f"🏦 **Next RBI MPC Meeting:** {next_mpc['Dates']} — {next_mpc['Meeting']}")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown("<p class='sec-label'>🏦 NSE Trading Holidays 2026</p>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(NSE_HOLIDAYS_2026), use_container_width=True, hide_index=True, height=520)
with c2:
    st.markdown("<p class='sec-label'>🏦 RBI MPC Meeting Dates 2026</p>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(RBI_MPC_2026), use_container_width=True, hide_index=True, height=240)
    st.markdown("<p class='sec-label' style='margin-top:1rem'>📈 Key Market Events 2026</p>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(KEY_EVENTS_2026), use_container_width=True, hide_index=True, height=280)

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
st.markdown("<p class='sec-label'>📆 NSE F&O Monthly Expiry Dates 2026</p>", unsafe_allow_html=True)
fo_expiry = [
    {"Month":"January","Expiry Date":"29 Jan 2026","Status":"✅ Past"},{"Month":"February","Expiry Date":"26 Feb 2026","Status":"✅ Past"},{"Month":"March","Expiry Date":"26 Mar 2026","Status":"✅ Past"},{"Month":"April","Expiry Date":"30 Apr 2026","Status":"✅ Past"},{"Month":"May","Expiry Date":"28 May 2026","Status":"✅ Past"},{"Month":"June","Expiry Date":"25 Jun 2026","Status":"🔜 Upcoming"},{"Month":"July","Expiry Date":"30 Jul 2026","Status":"🔜 Upcoming"},{"Month":"August","Expiry Date":"27 Aug 2026","Status":"🔜 Upcoming"},{"Month":"September","Expiry Date":"24 Sep 2026","Status":"🔜 Upcoming"},{"Month":"October","Expiry Date":"29 Oct 2026","Status":"🔜 Upcoming"},{"Month":"November","Expiry Date":"26 Nov 2026","Status":"🔜 Upcoming"},{"Month":"December","Expiry Date":"31 Dec 2026","Status":"🔜 Upcoming"},
]
st.dataframe(pd.DataFrame(fo_expiry), use_container_width=True, hide_index=True)
st.caption("⚠️ All dates are indicative. Verify with NSE official website before trading.")
