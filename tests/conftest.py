"""Shared fixtures for the test suite."""
import os
import sys
import types
import pytest

# ---------------------------------------------------------------------------
# Make the repo root importable without installing the package
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Stub heavy optional dependencies so unit tests never need real credentials
# ---------------------------------------------------------------------------

def _stub_module(name: str, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules.setdefault(name, mod)
    return mod

# Streamlit stub -- prevents ImportError when utils modules import st
_st = _stub_module(
    "streamlit",
    cache_data=lambda *a, **kw: (lambda f: f),
    session_state={},
    secrets={},
    error=lambda *a, **kw: None,
    warning=lambda *a, **kw: None,
    info=lambda *a, **kw: None,
    success=lambda *a, **kw: None,
)

_stub_module("supabase")
_stub_module("nselib")
_stub_module("nselib.capital_market")
_stub_module("streamlit_autorefresh")
