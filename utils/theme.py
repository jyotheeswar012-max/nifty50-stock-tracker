"""Theme injection helpers for the NSE Tracker Streamlit app.

Provides inject() and inject_topbar() used by app.py to apply
custom CSS/styling. Safe to call even if streamlit is not fully loaded.
"""
import streamlit as st


def inject() -> None:
    """Inject global CSS theme overrides."""
    st.markdown(
        """
        <style>
        /* ── NSE Tracker global theme ── */
        [data-testid="stAppViewContainer"] {
            background-color: #0f172a;
            color: #e2e8f0;
        }
        [data-testid="stSidebar"] {
            background-color: #1e293b;
        }
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1e293b;
            border-radius: 8px;
            padding: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            color: #94a3b8;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background-color: #334155 !important;
            color: #f1f5f9 !important;
            border-radius: 6px;
        }
        .metric-card {
            background: #1e293b;
            border-radius: 10px;
            padding: 16px;
            border: 1px solid #334155;
        }
        /* Better dataframe styling */
        [data-testid="stDataFrame"] {
            border: 1px solid #334155;
            border-radius: 8px;
        }
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_topbar() -> None:
    """Inject a custom top navigation bar."""
    st.markdown(
        """
        <style>
        .nse-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 12px 24px;
            border-bottom: 1px solid #334155;
            margin-bottom: 8px;
        }
        .nse-topbar-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: #38bdf8;
            letter-spacing: -0.5px;
        }
        .nse-topbar-subtitle {
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 2px;
        }
        </style>
        <div class="nse-topbar">
            <div>
                <div class="nse-topbar-title">📈 NSE & Nifty 50 Tracker</div>
                <div class="nse-topbar-subtitle">Real-time NSE market intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
