"""Central logging configuration for the NSE Tracker.

Every module obtains its logger via::

    from utils.logger import get_logger
    log = get_logger(__name__)

Log output goes to TWO handlers simultaneously:
  1. logs/app.log  — rotating file (5 MB × 3 backups), always written
  2. stderr        — WARNING+ only, so Streamlit Cloud captures critical issues

Format (both handlers)::

    2026-06-15 22:05:01 IST | INFO     | utils.data:_yf_history:87 | message
    <timestamp IST>         | <level>  | <module>:<func>:<lineno>  | <msg>

Usage levels (follow these conventions everywhere):
  log.debug()   — per-tick / per-row trace; disabled in production by default
  log.info()    — normal lifecycle events (source used, cache hit, market open)
  log.warning() — degraded-but-continuing situations (fallback active, stale data)
  log.error()   — recoverable failures (fetch failed, chart could not render)
  log.critical()— unrecoverable startup failures only

Environment overrides::

    LOG_LEVEL=DEBUG   # override via Streamlit Cloud → Secrets, or shell env
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_LOG_DIR  = Path("logs")
_LOG_FILE = _LOG_DIR / "app.log"
_FMT      = "%(asctime)s IST | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES   = 5 * 1024 * 1024   # 5 MB
_BACKUP_COUNT = 3

# Root level can be overridden via environment variable (useful for debugging)
_ROOT_LEVEL = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

# ---------------------------------------------------------------------------
# One-time setup (idempotent — safe to import multiple times)
# ---------------------------------------------------------------------------
_configured = False


def _setup() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    if root.handlers:          # already configured by another import path
        _configured = True
        return

    root.setLevel(_ROOT_LEVEL)

    formatter = logging.Formatter(fmt=_FMT, datefmt=_DATE_FMT)

    # --- Handler 1: rotating file -------------------------------------------
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            _LOG_FILE,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setLevel(_ROOT_LEVEL)
        fh.setFormatter(formatter)
        root.addHandler(fh)
    except Exception as exc:   # read-only filesystem (e.g. some cloud envs)
        # Don't crash the app; console-only logging still works
        logging.warning("Could not create log file %s: %s — logging to console only.", _LOG_FILE, exc)

    # --- Handler 2: console (WARNING+ only in production) --------------------
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # Silence noisy third-party loggers
    for noisy in ("yfinance", "peewee", "urllib3", "asyncio", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    _configured = True


_setup()   # run immediately on first import


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.  Call as ``get_logger(__name__)``."""
    return logging.getLogger(name)


def log_file_path() -> Path:
    """Return the absolute path to the current log file."""
    return _LOG_FILE.resolve()


def read_recent_logs(n: int = 100) -> list[str]:
    """Return the last *n* lines from the log file, newest-last.

    Returns an empty list if the file does not exist yet.
    """
    try:
        with open(_LOG_FILE, encoding="utf-8") as fh:
            lines = fh.readlines()
        return [l.rstrip() for l in lines[-n:]]
    except FileNotFoundError:
        return []
    except Exception:
        return []
