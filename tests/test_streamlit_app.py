"""Streamlit AppTest — smoke tests for every page/tab in the app.
Requires: pip install streamlit>=1.31 pytest
Run with:  pytest tests/test_streamlit_app.py -v
"""
import pytest
import os

# Guard: skip entire module if AppTest is not available
pytest.importorskip("streamlit.testing.v1", reason="Requires Streamlit >= 1.31")

from streamlit.testing.v1 import AppTest

# ── helpers ────────────────────────────────────────────────────────────────────

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "app.py")


def _run_app(timeout: int = 15) -> AppTest:
    """Helper: boot the app and run until stable."""
    at = AppTest.from_file(APP_PATH, default_timeout=timeout)
    at.run()
    return at


# ── Smoke tests ────────────────────────────────────────────────────────────────

class TestAppLoads:
    def test_no_exception_on_startup(self):
        at = _run_app()
        assert not at.exception, f"App raised exception: {at.exception}"

    def test_title_visible(self):
        at = _run_app()
        titles = [t.value for t in at.title]
        assert any("Nifty" in t or "nifty" in t.lower() for t in titles), \
            "Expected a Nifty 50 title element"

    def test_at_least_one_chart_rendered(self):
        at = _run_app()
        charts = (list(at.get("altair_chart")) +
                  list(at.get("plotly_chart")) +
                  list(at.get("line_chart")))
        assert len(charts) >= 1, "Expected at least one chart on the main page"


class TestSidebarControls:
    def test_sidebar_has_input_widgets(self):
        at = _run_app()
        widgets = list(at.sidebar.selectbox) + list(at.sidebar.radio) + list(at.sidebar.slider)
        assert len(widgets) >= 1, "Expected sidebar widgets for period/ticker selection"

    def test_period_selectbox_changes_output(self):
        at = _run_app()
        selectboxes = list(at.sidebar.selectbox)
        if selectboxes:
            selectboxes[0].set_value(selectboxes[0].options[-1])
            at.run()
            assert not at.exception


class TestKPIMetrics:
    def test_kpi_metrics_displayed(self):
        at = _run_app()
        metrics = list(at.metric)
        assert len(metrics) >= 1, "Expected at least one KPI metric (e.g. current price, return)"

    def test_no_none_values_in_metrics(self):
        at = _run_app()
        for metric in at.metric:
            assert metric.value is not None
            assert str(metric.value) != "None"


class TestDataTable:
    def test_dataframe_displayed(self):
        at = _run_app()
        tables = list(at.dataframe) + list(at.table)
        assert len(tables) >= 1, "Expected a data table (holdings or returns table)"


class TestErrorHandling:
    def test_no_error_messages_on_load(self):
        at = _run_app()
        errors = list(at.error)
        assert len(errors) == 0, f"Unexpected error messages: {[e.value for e in errors]}"

    def test_no_warnings_on_load(self):
        at = _run_app()
        warnings = list(at.warning)
        assert len(warnings) == 0, f"Unexpected warnings: {[w.value for w in warnings]}"
