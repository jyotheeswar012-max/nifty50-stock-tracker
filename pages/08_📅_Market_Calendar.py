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
    <div class="hero-sub"><span class="ui-badge badge-nse">NSE 2026</span>&nbsp; Holidays, RBI MPC dates &amp; key market events</div>
  </div>
</div>
""", unsafe_allow_html=True)

NSE_HOLIDAYS_2026 = [
    {"Date": "26 Jan 2026", "Day": "Monday",    "Holiday": "Republic Day"},
    {"Date": "19 Feb 2026", "Day": "Thursday",   "Holiday": "Chhatrapati Shivaji Maharaj Jayanti"},
    {"Date": "20 Mar 2026", "Day": "Friday",     "Holiday": "Good Friday"},
    {"Date": "30 Mar 2026", "Day": "Monday",     "Holiday": "Id-Ul-Fitr (Ramzan Id)"},
    {"Date": "14 Apr 2026", "Day": "Tuesday",    "Holiday": "Dr. Baba Saheb Ambedkar Jayanti"},
    {"Date": "01 May 2026", "Day": "Friday",     "Holiday": "Maharashtra Day"},
    {"Date": "22 May 2026", "Day": "Friday",     "Holiday": "Buddha Pournima"},
    {"Date": "07 Jun 2026", "Day": "Sunday",     "Holiday": "Id-Ul-Zuha (Bakri Id)"},
    {"Date": "06 Jul 2026", "Day": "Monday",     "Holiday": "Muharram"},
    {"Date": "15 Aug 2026", "Day": "Saturday",   "Holiday": "Independence Day"},
    {"Date": "02 Oct 2026", "Day": "Friday",     "Holiday": "Mahatma Gandhi Jayanti"},
    {"Date": "13 Oct 2026", "Day": "Tuesday",    "Holiday": "Dussehra"},
    {"Date": "20 Oct 2026", "Day": "Tuesday",    "Holiday": "Diwali — Laxmi Pujan (Muhurat Trading)"},
    {"Date": "21 Oct 2026", "Day": "Wednesday",  "Holiday": "Diwali — Balipratipada"},
    {"Date": "02 Nov 2026", "Day": "Monday",     "Holiday": "Guru Nanak Jayanti"},
    {"Date": "25 Dec 2026", "Day": "Friday",     "Holiday": "Christmas"},
]

RBI_MPC_2026 = [
    {"Meeting": "MPC #1", "Dates": "05–07 Feb 2026", "Decision": "Rate Cut 25bps → 6.25%",  "Status": "✅ Done"},
    {"Meeting": "MPC #2", "Dates": "07–09 Apr 2026", "Decision": "Rate Cut 25bps → 6.00%",  "Status": "✅ Done"},
    {"Meeting": "MPC #3", "Dates": "04–06 Jun 2026", "Decision": "Rate Cut 25bps → 5.75%",  "Status": "✅ Done"},
    {"Meeting": "MPC #4", "Dates": "05–07 Aug 2026", "Decision": "Awaited",                  "Status": "🔜 Upcoming"},
    {"Meeting": "MPC #5", "Dates": "29 Sep–01 Oct 2026","Decision": "Awaited",              "Status": "🔜 Upcoming"},
    {"Meeting": "MPC #6", "Dates": "02–04 Dec 2026", "Decision": "Awaited",                  "Status": "🔜 Upcoming"},
]

KEY_EVENTS_2026 = [
    {"Date": "01 Feb 2026",  "Event": "Union Budget 2026-27",             "Type": "Budget",    "Impact": "🔴 Very High"},
    {"Date": "15 Mar 2026",  "Event": "NSE F&O Expiry (Mar Series)",      "Type": "Expiry",    "Impact": "🟡 Medium"},
    {"Date": "01 Apr 2026",  "Event": "New Financial Year Begins",        "Type": "Calendar",  "Impact": "🟡 Medium"},
    {"Date": "Apr–May 2026", "Event": "Q4 FY26 Earnings Season",          "Type": "Earnings",  "Impact": "🔴 High"},
    {"Date": "Jun 2026",     "Event": "US Fed FOMC Meeting",              "Type": "Global",    "Impact": "🟡 Medium"},
    {"Date": "20 Oct 2026",  "Event": "Diwali Muhurat Trading Session",   "Type": "Special",   "Impact": "🟢 Positive"},
    {"Date": "Oct–Nov 2026", "Event": "Q2 FY27 Earnings Season",          "Type": "Earnings",  "Impact": "🔴 High"},
    {"Date": "Dec 2026",     "Event": "US Fed FOMC Meeting",              "Type": "Global",    "Impact": "🟡 Medium"},
    {"Date": "31 Mar 2027",  "Event": "Financial Year End",               "Type": "Calendar",  "Impact": "🟡 Medium"},
]

# ── Today highlight ──
today = date.today()
next_holiday = None
for h in NSE_HOLIDAYS_2026:
    try:
        hdate = datetime.strptime(h["Date"], "%d %b %Y").date()
        if hdate >= today:
            next_holiday = h
            break
    except Exception:
        pass

if next_holiday:
    st.info(f"🗓️ **Next NSE Holiday:** {next_holiday['Date']} — {next_holiday['Holiday']} ({next_holiday['Day']})")

# ── Next MPC highlight ──
for mpc in RBI_MPC_2026:
    if mpc["Status"] == "🔜 Upcoming":
        st.warning(f"🏦 **Next RBI MPC Meeting:** {mpc['Dates']} — {mpc['Meeting']}")
        break

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ── Two column layout ──
c1, c2 = st.columns(2)

with c1:
    st.markdown("<p class='sec-label'>🏦 NSE Trading Holidays 2026</p>", unsafe_allow_html=True)
    df_hol = pd.DataFrame(NSE_HOLIDAYS_2026)
    # Highlight past vs upcoming
    def highlight_holiday(row):
        try:
            hdate = datetime.strptime(row["Date"], "%d %b %Y").date()
            if hdate < today:
                return ["color: #94a3b8"] * len(row)
        except Exception:
            pass
        return [""] * len(row)
    st.dataframe(df_hol.style.apply(highlight_holiday, axis=1),
                 use_container_width=True, hide_index=True, height=520)

with c2:
    st.markdown("<p class='sec-label'>🏦 RBI MPC Meeting Dates 2026</p>", unsafe_allow_html=True)
    df_mpc = pd.DataFrame(RBI_MPC_2026)
    st.dataframe(df_mpc, use_container_width=True, hide_index=True, height=260)

    st.markdown("<p class='sec-label' style='margin-top:1.2rem'>📈 Key Market Events 2026</p>", unsafe_allow_html=True)
    df_events = pd.DataFrame(KEY_EVENTS_2026)
    st.dataframe(df_events, use_container_width=True, hide_index=True, height=340)

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ── F&O Expiry Calendar ──
st.markdown("<p class='sec-label'>📆 NSE F&O Monthly Expiry Dates 2026</p>", unsafe_allow_html=True)
fo_expiry = [
    {"Month": "January",   "Expiry Date": "29 Jan 2026", "Status": "✅ Past"},
    {"Month": "February",  "Expiry Date": "26 Feb 2026", "Status": "✅ Past"},
    {"Month": "March",     "Expiry Date": "26 Mar 2026", "Status": "✅ Past"},
    {"Month": "April",     "Expiry Date": "30 Apr 2026", "Status": "✅ Past"},
    {"Month": "May",       "Expiry Date": "28 May 2026", "Status": "✅ Past"},
    {"Month": "June",      "Expiry Date": "25 Jun 2026", "Status": "🔜 Upcoming"},
    {"Month": "July",      "Expiry Date": "30 Jul 2026", "Status": "🔜 Upcoming"},
    {"Month": "August",    "Expiry Date": "27 Aug 2026", "Status": "🔜 Upcoming"},
    {"Month": "September", "Expiry Date": "24 Sep 2026", "Status": "🔜 Upcoming"},
    {"Month": "October",   "Expiry Date": "29 Oct 2026", "Status": "🔜 Upcoming"},
    {"Month": "November",  "Expiry Date": "26 Nov 2026", "Status": "🔜 Upcoming"},
    {"Month": "December",  "Expiry Date": "31 Dec 2026", "Status": "🔜 Upcoming"},
]
df_fo = pd.DataFrame(fo_expiry)
st.dataframe(df_fo, use_container_width=True, hide_index=True)
st.caption("⚠️ All dates are indicative. Verify with NSE official website before trading.")
