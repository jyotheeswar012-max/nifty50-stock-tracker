"""Mobile-responsive CSS injection for the NSE Tracker.

Call inject_mobile_css() once at the start of app.py to apply
responsive styles that make the dashboard work well on phones and tablets.
"""
import streamlit as st


def inject_mobile_css() -> None:
    """Inject responsive CSS for mobile devices."""
    st.markdown(
        """
        <style>
        /* ── Mobile-first responsive tweaks ── */
        @media (max-width: 768px) {
            /* Stack columns on small screens */
            [data-testid="column"] {
                min-width: 100% !important;
            }
            /* Smaller tab labels */
            .stTabs [data-baseweb="tab"] {
                font-size: 0.75rem !important;
                padding: 6px 8px !important;
            }
            /* Compact metrics */
            [data-testid="stMetric"] {
                padding: 8px !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.1rem !important;
            }
            /* Full-width charts */
            [data-testid="stPlotlyChart"] {
                width: 100% !important;
            }
            /* Compact sidebar */
            [data-testid="stSidebar"] {
                width: 280px !important;
            }
        }
        @media (max-width: 480px) {
            .stTabs [data-baseweb="tab-list"] {
                flex-wrap: wrap;
            }
            .stTabs [data-baseweb="tab"] {
                font-size: 0.65rem !important;
                padding: 4px 6px !important;
            }
        }
        /* Touch-friendly tap targets */
        button, .stButton > button {
            min-height: 44px;
        }
        /* Better scrollbars */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #1e293b; }
        ::-webkit-scrollbar-thumb { background: #475569; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #64748b; }
        </style>
        """,
        unsafe_allow_html=True,
    )
