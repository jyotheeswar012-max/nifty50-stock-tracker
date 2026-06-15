"""Streamlit AppTest smoke-tests — every tab must load without an exception.

These tests start the full Streamlit app via AppTest and require a live
network connection (yfinance is mocked, but Streamlit itself boots fully).

Marked as 'slow' so they are skipped in the default CI run:
    pytest -m "not slow"       ← fast unit tests only (CI default)
    pytest -m slow             ← run smoke tests locally
    pytest                     ← run everything

Requirements:
    pip install 'streamlit>=1.31' pytest pytest-timeout

Run locally:
    pytest tests/test_streamlit_app.py -v --timeout=60
"""
from __future__ import annotations

import os
import pytest

# Guard: skip entire module when running in CI without display / Streamlit server.
pytest.importorskip("streamlit.testing.v1", reason="Requires Streamlit >= 1.31")

from streamlit.testing.v1 import AppTest

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")
_TIMEOUT  = int(os.getenv("APPTEST_TIMEOUT", "30"))  # seconds; override in CI

pytestmark = pytest.mark.slow   # skip in CI unless -m slow is passed


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _boot(timeout: int = _TIMEOUT) -> AppTest:
    """Boot the Streamlit app and run until stable.  Patches yfinance so no
    network calls are made during the smoke test."""
    import pandas as pd
    import numpy as np
    from unittest.mock import patch, MagicMock

    np.random.seed(0)
    dates = pd.date_range("2024-01-02", periods=10, freq="B")
    close = 21_000 + np.cumsum(np.random.randn(10) * 50)
    mock_df = pd.DataFrame(
        {"Open": close - 10, "High": close + 20, "Low": close - 20,
         "Close": close, "Volume": 200_000.0},
        index=dates,
    )

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_df

    at = AppTest.from_file(APP_PATH, default_timeout=timeout)
    with patch("yfinance.Ticker", return_value=mock_ticker):
        at.run()
    return at


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

class TestAppStartup:
    """Verify the app boots without any Python exception."""

    def test_no_unhandled_exception(self):
        at = _boot()
        assert not at.exception, (
            f"App raised an exception on startup:\n{at.exception}"
        )

    def test_page_config_applied(self):
        """App should render at least some visible text."""
        at = _boot()
        all_text = (
            [e.value for e in at.title]
            + [e.value for e in at.header]
            + [e.value for e in at.subheader]
            + [e.value for e in at.markdown]
        )
        assert len(all_text) > 0, "No visible text elements found — app may not have rendered"


class TestKPIMetrics:
    """At least one st.metric should be visible after startup."""

    def test_at_least_one_metric_rendered(self):
        at = _boot()
        assert len(list(at.metric)) >= 1, "Expected at least one KPI metric on the main page"

    def test_no_metric_value_is_none(self):
        at = _boot()
        for m in at.metric:
            assert m.value is not None, f"Metric '{m.label}' has None value"


class TestDataTable:
    """At least one st.dataframe / st.table should be visible."""

    def test_at_least_one_table_rendered(self):
        at = _boot()
        tables = list(at.dataframe) + list(at.table)
        assert len(tables) >= 1, "Expected at least one data table on the main page"


class TestNoErrorMessages:
    """The app must not surface st.error() or st.exception() to the user on clean load."""

    def test_no_st_error_on_load(self):
        at = _boot()
        errors = list(at.error)
        assert len(errors) == 0, (
            f"App displayed {len(errors)} st.error() message(s) on startup:\n"
            + "\n".join(e.value for e in errors)
        )


class TestTabNavigation:
    """Verify the app exposes the expected tabs."""

    def test_seven_tabs_exist(self):
        at = _boot()
        tabs = getattr(at, "tabs", None)
        if tabs is None:
            pytest.skip("at.tabs not available in this Streamlit version")
        assert len(list(tabs)) == 7, (
            f"Expected 7 tabs, found {len(list(tabs))}"
        )
