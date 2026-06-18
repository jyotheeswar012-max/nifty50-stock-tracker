import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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

# ── Shared chart theme ────────────────────────────────────────────────────────
PLT_LAYOUT = dict(
    paper_bgcolor="#ffffff", plot_bgcolor="#fafafa",
    font=dict(color="#1e293b", family="Inter, sans-serif", size=12),
    title_font=dict(size=15, color="#0f172a"),
    margin=dict(l=16, r=16, t=48, b=16),
)
_AXIS = dict(
    tickfont=dict(color="#1e293b", size=11),
    title_font=dict(color="#0f172a", size=12),
    linecolor="#cbd5e1", gridcolor="#f1f5f9", zerolinecolor="#cbd5e1",
)

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
    {"Date": "26 Jan 2026", "Day": "Monday",    "Holiday": "Republic Day"},
    {"Date": "19 Feb 2026", "Day": "Thursday",  "Holiday": "Chhatrapati Shivaji Maharaj Jayanti"},
    {"Date": "20 Mar 2026", "Day": "Friday",    "Holiday": "Good Friday"},
    {"Date": "30 Mar 2026", "Day": "Monday",    "Holiday": "Id-Ul-Fitr (Ramzan Id)"},
    {"Date": "14 Apr 2026", "Day": "Tuesday",   "Holiday": "Dr. Baba Saheb Ambedkar Jayanti"},
    {"Date": "01 May 2026", "Day": "Friday",    "Holiday": "Maharashtra Day"},
    {"Date": "22 May 2026", "Day": "Friday",    "Holiday": "Buddha Pournima"},
    {"Date": "06 Jul 2026", "Day": "Monday",    "Holiday": "Muharram"},
    {"Date": "15 Aug 2026", "Day": "Saturday",  "Holiday": "Independence Day"},
    {"Date": "02 Oct 2026", "Day": "Friday",    "Holiday": "Mahatma Gandhi Jayanti"},
    {"Date": "13 Oct 2026", "Day": "Tuesday",   "Holiday": "Dussehra"},
    {"Date": "20 Oct 2026", "Day": "Tuesday",   "Holiday": "Diwali — Laxmi Pujan (Muhurat Trading)"},
    {"Date": "21 Oct 2026", "Day": "Wednesday", "Holiday": "Diwali — Balipratipada"},
    {"Date": "02 Nov 2026", "Day": "Monday",    "Holiday": "Guru Nanak Jayanti"},
    {"Date": "25 Dec 2026", "Day": "Friday",    "Holiday": "Christmas"},
]

RBI_MPC_2026 = [
    {"Meeting": "MPC #1", "Dates": "05–07 Feb 2026", "Rate": 6.25, "Change": -0.25, "Decision": "Rate Cut 25bps → 6.25%", "Status": "✅ Done"},
    {"Meeting": "MPC #2", "Dates": "07–09 Apr 2026", "Rate": 6.00, "Change": -0.25, "Decision": "Rate Cut 25bps → 6.00%", "Status": "✅ Done"},
    {"Meeting": "MPC #3", "Dates": "04–06 Jun 2026", "Rate": 5.75, "Change": -0.25, "Decision": "Rate Cut 25bps → 5.75%", "Status": "✅ Done"},
    {"Meeting": "MPC #4", "Dates": "05–07 Aug 2026", "Rate": None, "Change": None, "Decision": "Awaited",               "Status": "🔜 Upcoming"},
    {"Meeting": "MPC #5", "Dates": "29 Sep–01 Oct 2026", "Rate": None, "Change": None, "Decision": "Awaited",          "Status": "🔜 Upcoming"},
    {"Meeting": "MPC #6", "Dates": "02–04 Dec 2026", "Rate": None, "Change": None, "Decision": "Awaited",              "Status": "🔜 Upcoming"},
]

KEY_EVENTS_2026 = [
    {"Date": "01 Feb 2026",    "Event": "Union Budget 2026-27",           "Type": "Budget",   "Impact": "🔴 Very High"},
    {"Date": "Apr–May 2026",   "Event": "Q4 FY26 Earnings Season",        "Type": "Earnings", "Impact": "🔴 High"},
    {"Date": "Jun 2026",       "Event": "US Fed FOMC Meeting",            "Type": "Global",   "Impact": "🟡 Medium"},
    {"Date": "20 Oct 2026",    "Event": "Diwali Muhurat Trading",          "Type": "Special",  "Impact": "🟢 Positive"},
    {"Date": "Oct–Nov 2026",   "Event": "Q2 FY27 Earnings Season",        "Type": "Earnings", "Impact": "🔴 High"},
    {"Date": "Dec 2026",       "Event": "US Fed FOMC Meeting",            "Type": "Global",   "Impact": "🟡 Medium"},
]

today = date.today()
next_holiday = next(
    (h for h in NSE_HOLIDAYS_2026 if datetime.strptime(h["Date"], "%d %b %Y").date() >= today),
    None,
)
if next_holiday:
    st.info(f"🗓️ **Next NSE Holiday:** {next_holiday['Date']} — {next_holiday['Holiday']} ({next_holiday['Day']})")

next_mpc = next((m for m in RBI_MPC_2026 if m["Status"] == "🔜 Upcoming"), None)
if next_mpc:
    st.warning(f"🏦 **Next RBI MPC Meeting:** {next_mpc['Dates']} — {next_mpc['Meeting']}")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ── RBI Repo Rate Visual Timeline ────────────────────────────────────────────
st.markdown("<p class='sec-label'>RBI Repo Rate Journey 2026</p>", unsafe_allow_html=True)
try:
    rate_labels = ["Start (6.50%)", "MPC #1 Feb", "MPC #2 Apr", "MPC #3 Jun", "MPC #4 Aug", "MPC #5 Oct", "MPC #6 Dec"]

    fig_rate = go.Figure()
    # Confirmed rate bars
    fig_rate.add_trace(go.Bar(
        x=rate_labels[:4],
        y=[6.50, 6.25, 6.00, 5.75],
        text=["6.50%", "6.25%", "6.00%", "5.75%"],
        textposition="outside",
        textfont=dict(color="#1e293b", size=12, family="Inter, sans-serif"),
        marker_color=["#94a3b8", "#10b981", "#10b981", "#10b981"],
        name="Confirmed Rate",
        width=0.5,
    ))
    # Projected / TBD bars
    fig_rate.add_trace(go.Bar(
        x=rate_labels[4:],
        y=[5.75, 5.75, 5.75],
        text=["TBD", "TBD", "TBD"],
        textposition="outside",
        textfont=dict(color="#64748b", size=12, family="Inter, sans-serif"),
        marker_color="#e2e8f0",
        marker_line_color="#94a3b8",
        marker_line_width=1.5,
        name="Projected / Awaited",
        opacity=0.7,
        width=0.5,
    ))
    # Rate cut arrows
    for x0, x1, y0, y1 in [(1, 2, 6.25, 6.00), (2, 3, 6.00, 5.75)]:
        fig_rate.add_annotation(
            x=rate_labels[x1], y=y1 + 0.05,
            ax=rate_labels[x0], ay=y0 + 0.05,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.2,
            arrowcolor="#10b981", arrowwidth=2,
        )
    fig_rate.update_layout(
        **PLT_LAYOUT, height=380,
        title="RBI Repo Rate — Confirmed Cuts & Upcoming MPC Meetings (2026)",
        xaxis=dict(**_AXIS, title="MPC Meeting"),
        yaxis=dict(**_AXIS, title="Repo Rate (%)", range=[5.0, 7.2], ticksuffix="%"),
        barmode="group",
        legend=dict(
            font=dict(color="#1e293b", size=12),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#e2e8f0", borderwidth=1,
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        ),
    )
    st.plotly_chart(fig_rate, use_container_width=True)
except Exception as e:
    st.warning(f"Rate chart error: {e}")

# ── F&O Expiry Visual Bar Chart ───────────────────────────────────────────────
st.markdown("<p class='sec-label'>NSE F&amp;O Monthly Expiry Status 2026</p>", unsafe_allow_html=True)
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
try:
    df_fo = pd.DataFrame(fo_expiry)
    month_order = ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"]
    df_fo["Month"] = pd.Categorical(df_fo["Month"], categories=month_order, ordered=True)
    df_fo["Is_Past"] = df_fo["Status"].str.contains("Past").astype(int)
    df_fo["Color"] = df_fo["Is_Past"].map({1: "✅ Past", 0: "🔜 Upcoming"})

    fig_fo = px.bar(
        df_fo, x="Month", y=[1] * 12,
        color="Color",
        color_discrete_map={"✅ Past": "#10b981", "🔜 Upcoming": "#6366f1"},
        text="Expiry Date",
        title="NSE F&O Monthly Expiry Dates 2026 — Past vs Upcoming",
        height=340,
        labels={"y": "", "Color": "Status"},
    )
    fig_fo.update_traces(
        textposition="inside",
        textfont=dict(color="#ffffff", size=11, family="Inter, sans-serif"),
    )
    fig_fo.update_yaxes(visible=False)
    fig_fo.update_layout(
        **PLT_LAYOUT,
        showlegend=True,
        xaxis=dict(**_AXIS, title="Month"),
        legend=dict(
            font=dict(color="#1e293b", size=12),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="#e2e8f0", borderwidth=1,
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        ),
    )
    st.plotly_chart(fig_fo, use_container_width=True)
except Exception as e:
    st.warning(f"F&O chart error: {e}")

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)

# ── Tables ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.markdown("<p class='sec-label'>🏦 NSE Trading Holidays 2026</p>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(NSE_HOLIDAYS_2026), use_container_width=True, hide_index=True, height=520)
with c2:
    st.markdown("<p class='sec-label'>🏦 RBI MPC Meeting Dates 2026</p>", unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame(RBI_MPC_2026)[["Meeting", "Dates", "Decision", "Status"]],
        use_container_width=True, hide_index=True, height=240,
    )
    st.markdown("<p class='sec-label' style='margin-top:1rem'>📈 Key Market Events 2026</p>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(KEY_EVENTS_2026), use_container_width=True, hide_index=True, height=280)

st.markdown('<hr class="ui-divider">', unsafe_allow_html=True)
st.markdown("<p class='sec-label'>📆 NSE F&O Monthly Expiry Dates 2026</p>", unsafe_allow_html=True)
st.dataframe(pd.DataFrame(fo_expiry), use_container_width=True, hide_index=True)
st.caption("⚠️ All dates are indicative. Verify with NSE official website before trading.")
