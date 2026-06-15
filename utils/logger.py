"""Central logging configuration for NSE Tracker.

Call ``get_logger(__name__)`` at the top of every module:

    from utils.logger import get_logger
    log = get_logger(__name__)

That's it.  The first call to this module sets up:
  - A rotating file handler  -> logs/app.log  (5 MB x 3 backups)
  - A console (stderr) handler at WARNING level so Streamlit's UI stays clean
  - ISO-8601 timestamps, log level, module name, and line number in every record

Environment override
--------------------
Set  LOG_LEVEL=DEBUG  (or INFO / WARNING / ERROR) in your environment or
in .streamlit/secrets.toml to change verbosity without touching code:

    [general]
    LOG_LEVEL = "DEBUG"
"""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR   = _REPO_ROOT / "logs"
_LOG_FILE  = _LOG_DIR / "app.log"

# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------
_FMT = (
    "%(asctime)s  %(levelname)-8s  %(name)s:%(lineno)d  |  %(message)s"
)
_DATE_FMT = "%Y-%m-%dT%H:%M:%S%z"   # ISO-8601, e.g. 2026-06-15T22:05:01+0530

# ---------------------------------------------------------------------------
# Internal state — only configure once per process
# ---------------------------------------------------------------------------
_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    # ---- resolve log level from env / Streamlit secrets ----
    level_name = os.environ.get("LOG_LEVEL", "").upper()
    if not level_name:
        try:
            import streamlit as st
            level_name = st.secrets.get("general", {}).get("LOG_LEVEL", "INFO").upper()
        except Exception:
            level_name = "INFO"
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger("nse_tracker")
    root.setLevel(level)

    # Avoid duplicate handlers if Streamlit hot-reloads the module
    if root.handlers:
        return

    formatter = logging.Formatter(fmt=_FMT, datefmt=_DATE_FMT)

    # ---- Rotating file handler ----
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=5 * 1024 * 1024,   # 5 MB per file
            backupCount=3,               # keep app.log, app.log.1, app.log.2, app.log.3
            encoding="utf-8",
        )
        fh.setLevel(level)
        fh.setFormatter(formatter)
        root.addHandler(fh)
    except Exception as exc:
        # Never crash the app just because we can't write a log file
        print(f"[logger] Could not create file handler: {exc}", file=sys.stderr)

    # ---- Console handler (WARNING+ only, keeps Streamlit UI clean) ----
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    root.debug("Logging initialised — writing to %s (level=%s)", _LOG_FILE, level_name)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'nse_tracker' hierarchy.

    Usage::

        from utils.logger import get_logger
        log = get_logger(__name__)   # e.g. 'nse_tracker.utils.data'

    The returned logger inherits level and handlers from the root
    'nse_tracker' logger configured here.
    """
    _configure()
    # Prefix every module logger so they all route through 'nse_tracker'
    child_name = name if name.startswith("nse_tracker") else f"nse_tracker.{name}"
    return logging.getLogger(child_name)
