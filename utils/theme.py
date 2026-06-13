"""
utils/theme.py  —  NSE Tracker Design System v3
Premium light theme: strong contrast, colorful accents, zero invisible text.
"""
import streamlit as st

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* =============================================
   RESET & BASE
   ============================================= */
*, *::before, *::after { box-sizing: border-box; }

.stApp {
  background: #f0f2f6 !important;
  color: #0f172a !important;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}

.block-container {
  padding-top: 1rem !important;
  padding-bottom: 3rem !important;
  max-width: 1280px !important;
}

/* kill excessive streamlit gaps */
.element-container { margin-bottom: 0.6rem !important; }
.stMarkdown p { margin: 0 0 0.3rem 0 !important; line-height: 1.6 !important; }

/* =============================================
   SIDEBAR
   ============================================= */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1e1b4b 0%, #312e81 40%, #1e1b4b 100%) !important;
  border-right: none !important;
}
[data-testid="stSidebar"] * { color: #e0e7ff !important; }
[data-testid="stSidebar"] .stRadio label {
  font-size: 0.88rem !important;
  font-weight: 500 !important;
  color: #c7d2fe !important;
  padding: 5px 0 !important;
  transition: color .15s !important;
}
[data-testid="stSidebar"] .stRadio label:hover { color: #ffffff !important; }
[data-testid="stSidebar"] hr {
  border: none !important;
  border-top: 1px solid rgba(255,255,255,.15) !important;
  margin: .7rem 0 !important;
}
[data-testid="stSidebar"] [data-testid="stCaption"] {
  color: #818cf8 !important;
  font-size: 0.76rem !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong,
[data-testid="stSidebar"] b { color: #ffffff !important; }
[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,.12) !important;
  color: #e0e7ff !important;
  border: 1px solid rgba(255,255,255,.2) !important;
  border-radius: 8px !important;
  font-size: 0.84rem !important;
  width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,.22) !important;
  color: #ffffff !important;
}

/* =============================================
   TOP BAR
   ============================================= */
[data-testid="stHeader"] {
  background: rgba(240,242,246,.95) !important;
  backdrop-filter: blur(10px) !important;
  border-bottom: 1px solid #e2e8f0 !important;
}

/* =============================================
   HERO BANNER  (replaces pg-hero)
   ============================================= */
.hero-banner {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #a21caf 100%);
  border-radius: 16px;
  padding: 1.4rem 2rem 1.2rem 2rem;
  margin-bottom: 1.4rem;
  display: flex;
  align-items: center;
  gap: 1.2rem;
  box-shadow: 0 4px 24px rgba(79,70,229,.25);
}
.hero-banner .hero-icon {
  font-size: 2.6rem;
  line-height: 1;
}
.hero-banner .hero-title {
  font-size: 1.7rem;
  font-weight: 900;
  color: #ffffff !important;
  margin: 0;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.hero-banner .hero-sub {
  font-size: 0.85rem;
  color: rgba(255,255,255,.8) !important;
  margin: 4px 0 0 0;
  display: flex;
  align-items: center;
  gap: .5rem;
  flex-wrap: wrap;
}

/* =============================================
   METRIC CARDS
   ============================================= */
[data-testid="metric-container"] {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 14px !important;
  border-left: 4px solid #6366f1 !important;
  padding: .9rem 1.1rem !important;
  box-shadow: 0 2px 8px rgba(15,23,42,.07) !important;
}
[data-testid="metric-container"] label {
  color: #475569 !important;
  font-size: 0.74rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: .07em !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: #0f172a !important;
  font-size: 1.5rem !important;
  font-weight: 800 !important;
  line-height: 1.2 !important;
}
[data-testid="stMetricDelta"] {
  font-size: 0.84rem !important;
  font-weight: 700 !important;
}

/* =============================================
   DATAFRAMES / TABLES
   ============================================= */
[data-testid="stDataFrame"] > div {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 1px 6px rgba(15,23,42,.06) !important;
}

/* =============================================
   BUTTONS
   ============================================= */
.stButton > button {
  border-radius: 9px !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  transition: all .15s ease !important;
  border: none !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: #ffffff !important;
  box-shadow: 0 3px 12px rgba(99,102,241,.35) !important;
}
.stButton > button[kind="primary"]:hover {
  filter: brightness(1.08) !important;
  box-shadow: 0 5px 18px rgba(99,102,241,.45) !important;
}
.stButton > button[kind="secondary"] {
  background: #f1f5f9 !important;
  color: #4338ca !important;
  border: 1.5px solid #c7d2fe !important;
}
.stButton > button[kind="secondary"]:hover {
  background: #e0e7ff !important;
}

/* =============================================
   INPUTS
   ============================================= */
.stTextInput input, .stNumberInput input,
.stSelectbox > div > div, .stTextArea textarea,
.stDateInput input {
  background: #ffffff !important;
  border: 1.5px solid #cbd5e1 !important;
  border-radius: 9px !important;
  color: #0f172a !important;
  font-size: 0.92rem !important;
  font-weight: 500 !important;
}
.stTextInput input:focus, .stNumberInput input:focus,
.stTextArea textarea:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
}

/* Selectbox label text */
.stSelectbox label, .stMultiSelect label,
.stSlider label, .stDateInput label,
.stNumberInput label, .stTextInput label {
  color: #374151 !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
}

/* =============================================
   ALERTS
   ============================================= */
[data-testid="stAlert"] {
  border-radius: 10px !important;
  font-weight: 500 !important;
}
.stSuccess > div {
  background: #f0fdf4 !important;
  border-left: 4px solid #22c55e !important;
  color: #166534 !important;
  font-weight: 600 !important;
}
.stError > div {
  background: #fff1f2 !important;
  border-left: 4px solid #f43f5e !important;
  color: #9f1239 !important;
  font-weight: 600 !important;
}
.stWarning > div {
  background: #fffbeb !important;
  border-left: 4px solid #f59e0b !important;
  color: #92400e !important;
  font-weight: 600 !important;
}
.stInfo > div {
  background: #eff6ff !important;
  border-left: 4px solid #3b82f6 !important;
  color: #1e3a8a !important;
  font-weight: 600 !important;
}

/* =============================================
   TABS
   ============================================= */
.stTabs [data-baseweb="tab-list"] {
  background: #e8edf5 !important;
  border-radius: 12px !important;
  padding: 4px !important;
  gap: 2px !important;
  border: none !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 9px !important;
  padding: 7px 20px !important;
  font-weight: 700 !important;
  font-size: 0.88rem !important;
  color: #475569 !important;
  background: transparent !important;
}
.stTabs [aria-selected="true"] {
  background: #ffffff !important;
  color: #4f46e5 !important;
  box-shadow: 0 2px 8px rgba(79,70,229,.18) !important;
}

/* =============================================
   SLIDERS
   ============================================= */
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: #6366f1 !important;
  border: 2px solid #fff !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.25) !important;
}

/* =============================================
   SCROLLBAR
   ============================================= */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #a5b4fc; border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: #6366f1; }

/* =============================================
   SECTION LABEL  (visible, not faint)
   ============================================= */
.sec-label {
  font-size: 0.76rem !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
  letter-spacing: .1em !important;
  color: #6366f1 !important;
  margin: 1rem 0 .5rem 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: .4rem !important;
}
.sec-label::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 14px;
  background: #6366f1;
  border-radius: 2px;
}

/* =============================================
   DIVIDER
   ============================================= */
.ui-divider {
  height: 1px;
  background: linear-gradient(90deg, #6366f1 0%, #e2e8f0 60%, transparent 100%);
  border: none;
  margin: 1.2rem 0 .8rem 0;
}

/* =============================================
   BADGES
   ============================================= */
.ui-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 11px;
  border-radius: 20px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: .05em;
  white-space: nowrap;
  text-transform: uppercase;
}
.badge-live { background: #dcfce7; color: #14532d !important; border: 1.5px solid #86efac; }
.badge-hist { background: #dbeafe; color: #1e3a8a !important; border: 1.5px solid #93c5fd; }
.badge-sim  { background: #fef9c3; color: #713f12 !important; border: 1.5px solid #fde047; }
.badge-nse  { background: #ede9fe; color: #3b0764 !important; border: 1.5px solid #c4b5fd; }
.badge-red  { background: #ffe4e6; color: #881337 !important; border: 1.5px solid #fda4af; }

/* =============================================
   CONTENT CARD  (subtle white surface)
   ============================================= */
.content-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 1.2rem 1.5rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 10px rgba(15,23,42,.06);
  margin-bottom: .8rem;
}

/* =============================================
   STAT ROW  (colored number pills)
   ============================================= */
.stat-chip {
  display: inline-block;
  background: linear-gradient(135deg,#4f46e5,#7c3aed);
  color: #ffffff !important;
  font-weight: 800;
  font-size: 1.1rem;
  border-radius: 10px;
  padding: .4rem 1rem;
  min-width: 64px;
  text-align: center;
}

/* =============================================
   PLOTLY CHARTS
   ============================================= */
.js-plotly-plot .plotly .bg { fill: #ffffff !important; }

/* =============================================
   EXPANDERS
   ============================================= */
.streamlit-expanderHeader {
  background: #f8fafc !important;
  border-radius: 9px !important;
  color: #3730a3 !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  border: 1px solid #e0e7ff !important;
}

/* =============================================
   GENERAL TEXT VISIBILITY
   ============================================= */
h1, h2, h3, h4, h5, h6 {
  color: #0f172a !important;
  font-weight: 800 !important;
}
p, span, li, td, th, label, div {
  color: #1e293b !important;
}
[data-testid="stMarkdownContainer"] p {
  color: #1e293b !important;
  font-size: 0.95rem !important;
}
</style>
"""


def inject():
    """Call once at the top of every page."""
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
