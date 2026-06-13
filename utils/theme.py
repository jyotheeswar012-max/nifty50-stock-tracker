"""
utils/theme.py
Shared light-theme CSS injected on every page.
"""
import streamlit as st

LIGHT_CSS = """
<style>
/* ── Base ─────────────────────────────────────────────── */
.stApp {
  background: linear-gradient(135deg, #f0f7ff 0%, #fafffe 50%, #f5f0ff 100%) !important;
  color: #1a1a2e !important;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #ffffff 0%, #f0f7ff 100%) !important;
  border-right: 1px solid #e0eaff !important;
  box-shadow: 2px 0 12px rgba(99,102,241,0.07) !important;
}
[data-testid="stSidebar"] * { color: #1a1a2e !important; }
[data-testid="stSidebar"] .stRadio label { color: #374151 !important; }
[data-testid="stSidebar"] hr { border-color: #e0eaff !important; }

/* ── Top bar ──────────────────────────────────────────── */
[data-testid="stHeader"] {
  background: rgba(255,255,255,0.85) !important;
  backdrop-filter: blur(12px) !important;
  border-bottom: 1px solid #e0eaff !important;
}

/* ── Metric cards ────────────────────────────────────── */
[data-testid="metric-container"] {
  background: #ffffff !important;
  border: 1px solid #e0eaff !important;
  border-radius: 16px !important;
  padding: 1rem 1.2rem !important;
  box-shadow: 0 2px 12px rgba(99,102,241,0.08) !important;
  transition: transform .2s, box-shadow .2s !important;
}
[data-testid="metric-container"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 20px rgba(99,102,241,0.14) !important;
}
[data-testid="metric-container"] label {
  color: #6366f1 !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: #1a1a2e !important;
  font-size: 1.6rem !important;
  font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.85rem !important; font-weight: 600 !important; }

/* ── DataFrames ──────────────────────────────────────── */
[data-testid="stDataFrame"] > div {
  background: #ffffff !important;
  border: 1px solid #e0eaff !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  box-shadow: 0 2px 12px rgba(99,102,241,0.06) !important;
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  transition: all .2s !important;
  border: none !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 14px rgba(99,102,241,0.35) !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 6px 20px rgba(99,102,241,0.45) !important;
  transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
  background: #f0f7ff !important;
  color: #6366f1 !important;
  border: 1px solid #c7d2fe !important;
}
.stButton > button[kind="secondary"]:hover {
  background: #e0e7ff !important;
  transform: translateY(-1px) !important;
}

/* ── Inputs ──────────────────────────────────────────── */
.stTextInput input, .stNumberInput input, .stSelectbox > div > div {
  background: #ffffff !important;
  border: 1.5px solid #c7d2fe !important;
  border-radius: 10px !important;
  color: #1a1a2e !important;
  font-size: 0.95rem !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
  outline: none !important;
}

/* ── Alerts / banners ────────────────────────────────── */
.stSuccess {
  background: linear-gradient(135deg, #d1fae5, #ecfdf5) !important;
  border-left: 4px solid #10b981 !important;
  border-radius: 12px !important;
  color: #065f46 !important;
}
.stError {
  background: linear-gradient(135deg, #fee2e2, #fff5f5) !important;
  border-left: 4px solid #ef4444 !important;
  border-radius: 12px !important;
  color: #991b1b !important;
}
.stWarning {
  background: linear-gradient(135deg, #fef3c7, #fffbeb) !important;
  border-left: 4px solid #f59e0b !important;
  border-radius: 12px !important;
  color: #92400e !important;
}
.stInfo {
  background: linear-gradient(135deg, #dbeafe, #eff6ff) !important;
  border-left: 4px solid #3b82f6 !important;
  border-radius: 12px !important;
  color: #1e40af !important;
}

/* ── Tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: #f0f4ff !important;
  border-radius: 14px !important;
  padding: 5px !important;
  gap: 4px !important;
  border: 1px solid #e0eaff !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px !important;
  padding: 8px 20px !important;
  font-weight: 600 !important;
  color: #6b7280 !important;
  background: transparent !important;
}
.stTabs [aria-selected="true"] {
  background: #ffffff !important;
  color: #6366f1 !important;
  box-shadow: 0 2px 8px rgba(99,102,241,0.18) !important;
}

/* ── Plotly charts background ─────────────────────────── */
.js-plotly-plot .plotly .bg {
  fill: #ffffff !important;
}

/* ── Expanders ───────────────────────────────────────── */
.streamlit-expanderHeader {
  background: #f0f4ff !important;
  border-radius: 10px !important;
  color: #4338ca !important;
  font-weight: 600 !important;
  border: 1px solid #e0eaff !important;
}

/* ── Sliders ─────────────────────────────────────────── */
.stSlider [data-baseweb="slider"] div[role="slider"] {
  background: #6366f1 !important;
  border: 2px solid #ffffff !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.3) !important;
}

/* ── Scrollbar ───────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f0f4ff; }
::-webkit-scrollbar-thumb { background: #c7d2fe; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #6366f1; }

/* ── Custom card class ───────────────────────────────── */
.ui-card {
  background: #ffffff;
  border: 1px solid #e0eaff;
  border-radius: 18px;
  padding: 1.5rem 1.8rem;
  box-shadow: 0 4px 16px rgba(99,102,241,0.08);
  margin-bottom: 1rem;
  transition: box-shadow .2s, transform .2s;
}
.ui-card:hover {
  box-shadow: 0 8px 28px rgba(99,102,241,0.14);
  transform: translateY(-2px);
}
.ui-badge {
  display: inline-block;
  padding: 3px 14px;
  border-radius: 20px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.badge-live   { background:#d1fae5; color:#065f46; border:1px solid #6ee7b7; }
.badge-hist   { background:#dbeafe; color:#1e40af; border:1px solid #93c5fd; }
.badge-sim    { background:#fef3c7; color:#92400e; border:1px solid #fcd34d; }
.badge-nse    { background:#ede9fe; color:#5b21b6; border:1px solid #c4b5fd; }
.ui-page-title {
  font-size: 2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 0.2rem;
}
.ui-caption {
  color: #6b7280;
  font-size: 0.92rem;
  margin-bottom: 1.2rem;
}
.stat-pill {
  background: linear-gradient(135deg, #f0f4ff, #faf5ff);
  border: 1px solid #e0eaff;
  border-radius: 12px;
  padding: 0.6rem 1rem;
  text-align: center;
  font-weight: 700;
  color: #4338ca;
}
</style>
"""

def inject():
    """Call once at the top of every page to apply the light theme."""
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
