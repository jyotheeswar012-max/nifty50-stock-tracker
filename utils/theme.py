"""
utils/theme.py  —  Shared design system (light, premium, clean)
"""
import streamlit as st

LIGHT_CSS = """
<style>
/* ════════════════════════════════════════════════════
   BASE
════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }

.stApp {
  background: #f8fafc !important;
  color: #0f172a !important;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}

/* hide Streamlit default top padding */
.block-container {
  padding-top: 1.5rem !important;
  padding-bottom: 2rem !important;
  max-width: 1200px !important;
}

/* ════════════════════════════════════════════════════
   SIDEBAR
════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: #ffffff !important;
  border-right: 1px solid #e2e8f0 !important;
  box-shadow: 1px 0 0 #e2e8f0 !important;
}
[data-testid="stSidebar"] * { color: #0f172a !important; }
[data-testid="stSidebar"] hr { border-color: #e2e8f0 !important; margin: .6rem 0 !important; }
[data-testid="stSidebar"] .stRadio label {
  font-size: 0.9rem !important;
  color: #475569 !important;
  padding: 4px 0 !important;
}
[data-testid="stSidebar"] .stRadio label:hover { color: #6366f1 !important; }
[data-testid="stSidebar"] [data-testid="stCaption"] {
  color: #94a3b8 !important;
  font-size: 0.78rem !important;
}

/* ════════════════════════════════════════════════════
   TOP BAR
════════════════════════════════════════════════════ */
[data-testid="stHeader"] {
  background: rgba(248,250,252,0.92) !important;
  backdrop-filter: blur(12px) !important;
  border-bottom: 1px solid #e2e8f0 !important;
}

/* ════════════════════════════════════════════════════
   METRIC CARDS
════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 14px !important;
  padding: .9rem 1.1rem !important;
  box-shadow: 0 1px 4px rgba(15,23,42,.06) !important;
}
[data-testid="metric-container"] label {
  color: #6366f1 !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: .06em !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: #0f172a !important;
  font-size: 1.45rem !important;
  font-weight: 700 !important;
  line-height: 1.2 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; font-weight: 600 !important; }

/* ════════════════════════════════════════════════════
   DATAFRAMES
════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] > div {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 1px 4px rgba(15,23,42,.05) !important;
}

/* ════════════════════════════════════════════════════
   BUTTONS
════════════════════════════════════════════════════ */
.stButton > button {
  border-radius: 9px !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  transition: all .15s ease !important;
  border: none !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  color: #fff !important;
  box-shadow: 0 3px 10px rgba(99,102,241,.32) !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 5px 16px rgba(99,102,241,.42) !important;
  filter: brightness(1.06) !important;
}
.stButton > button[kind="secondary"] {
  background: #f1f5f9 !important;
  color: #6366f1 !important;
  border: 1px solid #e0e7ff !important;
}
.stButton > button[kind="secondary"]:hover { background: #e0e7ff !important; }

/* ════════════════════════════════════════════════════
   INPUTS
════════════════════════════════════════════════════ */
.stTextInput input, .stNumberInput input,
.stSelectbox > div > div, .stTextArea textarea {
  background: #ffffff !important;
  border: 1.5px solid #cbd5e1 !important;
  border-radius: 9px !important;
  color: #0f172a !important;
  font-size: 0.92rem !important;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
  outline: none !important;
}

/* ════════════════════════════════════════════════════
   ALERTS
════════════════════════════════════════════════════ */
.stSuccess {
  background: #f0fdf4 !important;
  border-left: 3px solid #22c55e !important;
  border-radius: 10px !important;
  color: #15803d !important;
  padding: .7rem 1rem !important;
}
.stError {
  background: #fff1f2 !important;
  border-left: 3px solid #f43f5e !important;
  border-radius: 10px !important;
  color: #be123c !important;
  padding: .7rem 1rem !important;
}
.stWarning {
  background: #fffbeb !important;
  border-left: 3px solid #f59e0b !important;
  border-radius: 10px !important;
  color: #b45309 !important;
  padding: .7rem 1rem !important;
}
.stInfo {
  background: #eff6ff !important;
  border-left: 3px solid #3b82f6 !important;
  border-radius: 10px !important;
  color: #1d4ed8 !important;
  padding: .7rem 1rem !important;
}

/* ════════════════════════════════════════════════════
   TABS
════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
  background: #f1f5f9 !important;
  border-radius: 12px !important;
  padding: 4px !important;
  gap: 2px !important;
  border: 1px solid #e2e8f0 !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 9px !important;
  padding: 6px 18px !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  color: #64748b !important;
  background: transparent !important;
}
.stTabs [aria-selected="true"] {
  background: #ffffff !important;
  color: #6366f1 !important;
  box-shadow: 0 1px 6px rgba(99,102,241,.16) !important;
}

/* ════════════════════════════════════════════════════
   SLIDERS
════════════════════════════════════════════════════ */
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: #6366f1 !important;
  border: 2px solid #fff !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.25) !important;
}

/* ════════════════════════════════════════════════════
   SCROLLBAR
════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: #6366f1; }

/* ════════════════════════════════════════════════════
   PLOTLY CHARTS
════════════════════════════════════════════════════ */
.js-plotly-plot .plotly .bg { fill: #ffffff !important; }

/* ════════════════════════════════════════════════════
   EXPANDERS
════════════════════════════════════════════════════ */
.streamlit-expanderHeader {
  background: #f8fafc !important;
  border-radius: 9px !important;
  color: #4338ca !important;
  font-weight: 600 !important;
  border: 1px solid #e2e8f0 !important;
  font-size: 0.9rem !important;
}

/* ════════════════════════════════════════════════════
   DESIGN TOKENS — utility classes
════════════════════════════════════════════════════ */

/* Page hero header */
.pg-hero {
  padding: .2rem 0 1.2rem 0;
  margin-bottom: .2rem;
  border-bottom: 1px solid #e2e8f0;
}
.pg-hero h1 {
  font-size: 1.85rem;
  font-weight: 800;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 60%, #ec4899 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 .2rem 0;
  line-height: 1.2;
}
.pg-hero .sub {
  font-size: 0.88rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: .5rem;
  flex-wrap: wrap;
}

/* Section label (replaces h3/h4 in cards) */
.sec-label {
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: #94a3b8;
  margin: 0 0 .6rem 0;
}

/* Divider */
.ui-divider {
  height: 1px;
  background: linear-gradient(90deg, #e2e8f0 0%, transparent 100%);
  border: none;
  margin: 1.2rem 0;
}

/* Badges */
.ui-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: .05em;
  white-space: nowrap;
}
.badge-live { background:#dcfce7; color:#166534; border:1px solid #86efac; }
.badge-hist { background:#dbeafe; color:#1e40af; border:1px solid #93c5fd; }
.badge-sim  { background:#fef9c3; color:#854d0e; border:1px solid #fde047; }
.badge-nse  { background:#ede9fe; color:#5b21b6; border:1px solid #c4b5fd; }
.badge-red  { background:#ffe4e6; color:#9f1239; border:1px solid #fda4af; }

/* Inline stat pill (used in tables / summaries) */
.stat-pill {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: .4rem .9rem;
  text-align: center;
  font-weight: 700;
  font-size: 0.9rem;
  color: #4338ca;
  display: inline-block;
}

/* Accent strip (top-border accent on a section) */
.accent-strip {
  border-top: 3px solid;
  border-image: linear-gradient(90deg,#6366f1,#8b5cf6,#ec4899) 1;
  border-radius: 0 0 12px 12px;
  background: #ffffff;
  padding: 1rem 1.4rem 1.2rem 1.4rem;
  box-shadow: 0 1px 6px rgba(15,23,42,.06);
  margin-bottom: 1rem;
}

/* Reduce vertical gap between Streamlit elements */
.element-container { margin-bottom: .5rem !important; }
.stMarkdown p { margin-bottom: .4rem !important; }

/* Remove gap above page title */
.appview-container .main .block-container > :first-child { padding-top: 0 !important; }
</style>
"""


def inject():
    """Call once at the top of every page."""
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
