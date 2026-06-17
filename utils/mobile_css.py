"""Responsive / mobile-first CSS injected once at startup.

Call inject_mobile_css() from app.py.  All rules are scoped tightly
to avoid clobbering Streamlit internals.
"""
import streamlit as st


_CSS = """
<style>
/* ===== Mobile-first base ===== */
@media (max-width: 768px) {

    /* Full-width main area on phones */
    .main .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        max-width: 100% !important;
    }

    /* Sidebar: collapse to 260px, allow horizontal scroll on very small screens */
    section[data-testid="stSidebar"] {
        min-width: 260px !important;
        max-width: 85vw  !important;
    }

    /* Tab labels: smaller font so all 8 tabs stay visible */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.72rem !important;
        padding: 0.35rem 0.5rem !important;
        white-space: nowrap;
    }

    /* Metric cards: stack vertically */
    div[data-testid="column"] {
        min-width: 140px;
    }

    /* Plotly charts: allow horizontal scroll rather than squish */
    .js-plotly-plot, .plotly {
        min-width: 320px;
        overflow-x: auto;
    }

    /* st.dataframe: horizontal scroll */
    [data-testid="stDataFrame"] > div {
        overflow-x: auto !important;
    }

    /* Touch targets: buttons ≥ 44 × 44 px */
    button[kind], .stButton > button, .stDownloadButton > button {
        min-height: 44px !important;
        min-width: 44px !important;
        font-size: 0.9rem !important;
    }

    /* Slider thumbs easier to grab */
    [data-testid="stSlider"] [role="slider"] {
        width: 28px !important;
        height: 28px !important;
    }

    /* Number inputs: larger touch zone */
    input[type="number"] {
        font-size: 1rem !important;
        min-height: 40px !important;
    }

    /* Status banner: smaller text */
    .stAlert p {
        font-size: 0.82rem !important;
    }
}

/* ===== Tablet (768–992 px) ===== */
@media (min-width: 769px) and (max-width: 992px) {

    .stTabs [data-baseweb="tab"] {
        font-size: 0.80rem !important;
        padding: 0.4rem 0.7rem !important;
    }

    .main .block-container {
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }
}

/* ===== Common: download button polish ===== */
.stDownloadButton > button {
    border: 1px solid #6366f1 !important;
    color: #6366f1 !important;
    background: transparent !important;
    transition: background 0.15s, color 0.15s;
}
.stDownloadButton > button:hover {
    background: #6366f1 !important;
    color: #ffffff !important;
}

/* ===== Common: spinner contrast ===== */
[data-testid="stSpinner"] p {
    font-size: 0.9rem;
    color: #6366f1;
    font-weight: 500;
}
</style>
"""


def inject_mobile_css() -> None:
    """Inject responsive CSS into the Streamlit page (idempotent)."""
    st.markdown(_CSS, unsafe_allow_html=True)
