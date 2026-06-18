"""
utils/theme.py  -  NSE Tracker  -  Full-width Fixed Top Navbar
"""
import streamlit as st

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body { background: #f0f2f6 !important; }
.stApp {
  background: #f0f2f6 !important;
  font-family: 'Inter','Segoe UI',system-ui,sans-serif !important;
}
[data-testid="stHeader"] { display: none !important; }

/* ═══════════════════════════════════════════════════════
   GLOBAL BLACK TEXT OVERRIDE — every element in the app
   ═══════════════════════════════════════════════════════ */
.stApp *,
.stApp p,
.stApp span,
.stApp div,
.stApp label,
.stApp li,
.stApp td,
.stApp th,
.stApp strong,
.stApp em,
.stApp b,
.stApp small,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6,
.stApp a,
.stApp button,
.stApp input,
.stApp textarea,
.stApp select,
.stApp option,
[data-testid="stMarkdownContainer"] *,
[data-testid="stMainBlockContainer"] *,
[data-testid="stVerticalBlock"] *,
[data-testid="stAppViewContainer"] *,
.block-container *,
.element-container *,
[data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"] *,
[data-testid="stMetricDelta"],
[data-testid="stCaptionContainer"] *,
.stTabs *,
.stSelectbox *,
.stMultiSelect *,
.stSlider *,
.stNumberInput *,
.stTextInput *,
.stTextArea *,
.stDateInput *,
.stRadio *,
.stCheckbox *,
.stSuccess *,
.stError *,
.stWarning *,
.stInfo *,
.streamlit-expanderHeader,
.streamlit-expanderHeader *,
.streamlit-expanderContent *,
[data-testid="stDataFrame"] *,
[data-baseweb="tab"] *,
[data-baseweb="select"] *,
[data-baseweb="input"] *,
[data-baseweb="textarea"] * {
  color: #000000 !important;
}

/* Keep white text ONLY on the top navbar and hero banner */
.nse-topbar,
.nse-topbar *,
.nse-topbar-brand,
.nse-topbar-brand *,
.nse-topbar-links a,
.nse-topbar-links a *,
.nse-market-pill,
.nse-market-pill *,
.hero-banner,
.hero-banner * {
  color: inherit !important;
}
.nse-topbar-brand .brand-name { color: #ffffff !important; }
.nse-topbar-brand .sub { color: #a5b4fc !important; }
.nse-topbar-links a { color: #c7d2fe !important; }
.nse-topbar-links a:hover,
.nse-topbar-links a.active { color: #ffffff !important; }
.nse-market-pill { color: #e0e7ff !important; }
.hero-banner, .hero-banner p, .hero-banner span, .hero-banner div,
.hero-banner strong, .hero-banner em, .hero-banner small,
.hero-banner h1, .hero-banner h2, .hero-banner h3,
.hero-banner .hero-title, .hero-banner .hero-sub { color: #ffffff !important; }

/* Primary buttons stay white text */
.stButton > button[kind="primary"],
.stButton > button[kind="primary"] * { color: #ffffff !important; }

/* Metric delta colours (green/red) — keep readable */
[data-testid="stMetricDelta"][data-direction="up"]   { color: #15803d !important; }
[data-testid="stMetricDelta"][data-direction="down"] { color: #b91c1c !important; }

/* ── HIDE SIDEBAR ── */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarFooter"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"],
div[data-testid="stSidebarCollapsedControl"] { display: none !important; width: 0 !important; }
[data-testid="stAppViewContainer"] > section:first-child { display: none !important; }
[data-testid="stMain"] { padding-top: 56px !important; margin-left: 0 !important; }
.block-container {
  padding-top: 0.8rem !important; padding-bottom: 3rem !important;
  max-width: 1280px !important; margin-left: auto !important; margin-right: auto !important;
}
.element-container { margin-bottom: 0.45rem !important; }

/* ──────────────── TOP NAVBAR ──────────────── */
.nse-topbar {
  position: fixed !important;
  top: 0 !important; left: 0 !important; right: 0 !important;
  width: 100vw !important; z-index: 99999 !important;
  background: linear-gradient(90deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
  height: 52px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  padding: 0 1.4rem;
  border-bottom: 2px solid rgba(99,102,241,.55);
  box-shadow: 0 3px 20px rgba(30,27,75,.45);
  gap: 1rem;
}
.nse-topbar-brand {
  display: flex; align-items: center; gap: 0.45rem;
  font-size: 0.95rem; font-weight: 900;
  white-space: nowrap; text-decoration: none !important;
  letter-spacing: -0.01em; flex-shrink: 0;
}
.nse-topbar-brand .logo-icon {
  width: 28px; height: 28px; flex-shrink: 0;
  background: rgba(255,255,255,0.15); border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem;
}
.nse-topbar-links {
  display: flex; align-items: center; justify-content: center;
  gap: 2px; flex-wrap: nowrap; overflow: hidden;
}
.nse-topbar-links a {
  display: inline-flex; align-items: center;
  padding: 5px 10px; border-radius: 7px;
  font-size: 0.76rem; font-weight: 600;
  text-decoration: none !important;
  white-space: nowrap; transition: background 0.15s, color 0.15s;
}
.nse-topbar-links a:hover  { background: rgba(255,255,255,0.14); }
.nse-topbar-links a.active { background: rgba(255,255,255,0.20); font-weight: 700; }
.nav-sep {
  width: 1px; height: 16px;
  background: rgba(255,255,255,0.18);
  margin: 0 4px; flex-shrink: 0;
}
.nse-topbar-right {
  display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;
}
.nse-market-pill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 11px; border-radius: 20px;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
  white-space: nowrap; border: 1.5px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.10);
}
.nse-market-pill .dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.dot-green { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
.dot-red   { background: #f87171; }

/* ── HERO BANNER ── */
.hero-banner {
  background: linear-gradient(135deg,#4f46e5 0%,#7c3aed 52%,#a21caf 100%);
  border-radius: 16px; padding: 1.4rem 2rem 1.2rem; margin-bottom: 1.4rem;
  display: flex; align-items: center; gap: 1.2rem;
  box-shadow: 0 4px 28px rgba(79,70,229,.28);
}
.hero-banner .hero-icon { font-size: 2.6rem; line-height: 1; }
.hero-banner .hero-title { font-size: 1.75rem !important; font-weight: 900 !important; margin: 0; letter-spacing: -.02em; line-height: 1.1; }
.hero-banner .hero-sub { font-size: 0.85rem !important; margin: 5px 0 0; display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }

/* ── BADGES ── */
.ui-badge {
  display: inline-flex !important; align-items: center !important; gap: 4px !important;
  padding: 3px 12px !important; border-radius: 20px !important; font-size: 0.72rem !important;
  font-weight: 800 !important; letter-spacing: .05em !important; white-space: nowrap !important;
  text-transform: uppercase !important; line-height: 1.4 !important;
}
.badge-live, .badge-live * { background:#dcfce7 !important; color:#14532d !important; border:1.5px solid #86efac; }
.badge-hist, .badge-hist * { background:#dbeafe !important; color:#1e3a8a !important; border:1.5px solid #93c5fd; }
.badge-sim,  .badge-sim  * { background:#fef9c3 !important; color:#713f12 !important; border:1.5px solid #fde047; }
.badge-nse,  .badge-nse  * { background:#ede9fe !important; color:#3b0764 !important; border:1.5px solid #c4b5fd; }
.badge-red,  .badge-red  * { background:#ffe4e6 !important; color:#881337 !important; border:1.5px solid #fda4af; }

/* ── METRICS ── */
[data-testid="metric-container"] {
  background: #ffffff !important; border: 1px solid #e2e8f0 !important;
  border-left: 4px solid #6366f1 !important; border-radius: 14px !important;
  padding: .9rem 1.1rem !important; box-shadow: 0 2px 8px rgba(15,23,42,.07) !important;
}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] > div {
  background: #ffffff !important; border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important; overflow: hidden !important;
  box-shadow: 0 1px 6px rgba(15,23,42,.06) !important;
}

/* ── BUTTONS ── */
.stButton > button { border-radius: 9px !important; font-weight: 700 !important; font-size: 0.9rem !important; transition: all .15s ease !important; }
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg,#6366f1,#8b5cf6) !important;
  border: none !important; box-shadow: 0 3px 12px rgba(99,102,241,.35) !important;
}
.stButton > button[kind="primary"]:hover { filter: brightness(1.08) !important; }
.stButton > button[kind="secondary"] { background: #f1f5f9 !important; border: 1.5px solid #c7d2fe !important; }
.stButton > button[kind="secondary"]:hover { background: #e0e7ff !important; }

/* ── INPUTS ── */
.stTextInput input, .stNumberInput input, .stSelectbox > div > div,
.stTextArea textarea, .stDateInput input {
  background: #ffffff !important; border: 1.5px solid #cbd5e1 !important;
  border-radius: 9px !important; font-size: 0.92rem !important; font-weight: 500 !important;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
  border-color: #6366f1 !important; box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
}

/* ── ALERTS ── */
.stSuccess > div { background:#f0fdf4 !important; border-left:4px solid #22c55e !important; border-radius:10px !important; }
.stError   > div { background:#fff1f2 !important; border-left:4px solid #f43f5e !important; border-radius:10px !important; }
.stWarning > div { background:#fffbeb !important; border-left:4px solid #f59e0b !important; border-radius:10px !important; }
.stInfo    > div { background:#eff6ff !important; border-left:4px solid #3b82f6 !important; border-radius:10px !important; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
  background: #e8edf5 !important; border-radius: 12px !important;
  padding: 4px !important; gap: 2px !important; border: none !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 9px !important; padding: 7px 18px !important;
  font-weight: 700 !important; font-size: 0.85rem !important;
  background: transparent !important;
}
.stTabs [aria-selected="true"] {
  background: #ffffff !important;
  box-shadow: 0 2px 8px rgba(79,70,229,.18) !important;
}

/* ── MISC ── */
.sec-label {
  font-size: 0.76rem !important; font-weight: 800 !important;
  text-transform: uppercase !important; letter-spacing: .1em !important;
  color: #6366f1 !important; margin: 1rem 0 .5rem !important;
  display: flex !important; align-items: center !important; gap: .5rem !important;
}
.sec-label::before { content: ''; display: inline-block; width: 3px; height: 14px; background: #6366f1; border-radius: 2px; flex-shrink: 0; }
.ui-divider { height: 1px; background: linear-gradient(90deg,#6366f1 0%,#e2e8f0 55%,transparent 100%); border: none; margin: 1.2rem 0 .8rem; }
.ui-card, .content-card {
  background: #ffffff !important; border-radius: 14px; padding: 1.3rem 1.6rem;
  border: 1px solid #e2e8f0; box-shadow: 0 2px 10px rgba(15,23,42,.06); margin-bottom: .9rem;
}
.stat-chip { display: inline-block; background: linear-gradient(135deg,#4f46e5,#7c3aed); font-weight: 800; font-size: 1.1rem; border-radius: 10px; padding: .4rem 1rem; min-width: 64px; text-align: center; }
.stat-chip * { color: #ffffff !important; }
.ui-page-title { font-size: 1.7rem !important; font-weight: 900 !important; line-height: 1.15 !important; margin: 0 0 .2rem !important; }
.ui-caption { font-size: 0.88rem !important; font-weight: 500 !important; margin: 0 !important; }
[data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] span { font-size: 0.8rem !important; }
.streamlit-expanderHeader { background: #f8fafc !important; border-radius: 9px !important; font-weight: 700 !important; font-size: 0.9rem !important; border: 1px solid #e0e7ff !important; }
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:#f1f5f9; }
::-webkit-scrollbar-thumb { background:#a5b4fc; border-radius:8px; }
::-webkit-scrollbar-thumb:hover { background:#6366f1; }
.js-plotly-plot .plotly .bg { fill: #ffffff !important; }
</style>
"""


def inject():
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)


def inject_topbar(user=None):
    """Full-width fixed top navbar with 3-column grid: brand | nav | status."""
    import datetime
    import pytz
    try:
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.datetime.now(ist)
        h, m = now.hour, now.minute
        is_open = (
            now.weekday() < 5
            and (h > 9 or (h == 9 and m >= 15))
            and (h < 15 or (h == 15 and m <= 30))
        )
        if is_open:
            dot_cls = "dot-green"
            mkt_label = "MARKET OPEN"
        else:
            dot_cls = "dot-red"
            mkt_label = "MARKET CLOSED"
    except Exception:
        dot_cls = "dot-red"
        mkt_label = "NSE"

    html = f"""
    <div class="nse-topbar">
      <a class="nse-topbar-brand" href="/" target="_self">
        <div class="logo-icon">📈</div>
        <span class="brand-name">NSE Tracker</span>
        <span class="sub">NIFTY 50</span>
      </a>
      <nav class="nse-topbar-links">
        <a href="/" target="_self">Overview</a>
        <div class="nav-sep"></div>
        <a href="/Scenario_Engine" target="_self">Scenario</a>
        <a href="/Paper_Portfolio" target="_self">Portfolio</a>
        <a href="/Paper_Trading" target="_self">Trading</a>
        <div class="nav-sep"></div>
        <a href="/News_Sentiment" target="_self">News</a>
        <a href="/ML_Predictions" target="_self">ML</a>
        <a href="/Market_Calendar" target="_self">Calendar</a>
        <div class="nav-sep"></div>
        <a href="/Alerts" target="_self">Alerts</a>
        <a href="/Watchlist" target="_self">Watchlist</a>
      </nav>
      <div class="nse-topbar-right">
        <div class="nse-market-pill">
          <span class="dot {dot_cls}"></span>
          {mkt_label}
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
