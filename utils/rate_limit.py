"""In-process sliding-window rate limiter.

Prevents the app from hammering Yahoo Finance or SMTP when multiple
Streamlit sessions run concurrently or when the Streamlit auto-refresh
fires faster than expected.

Usage
-----
    from utils.rate_limit import RateLimiter

    _yf_limiter   = RateLimiter(max_calls=10, window_s=60,  name="yfinance")
    _smtp_limiter = RateLimiter(max_calls=5,  window_s=300, name="smtp")

    # In a fetch function:
    ok, wait = _yf_limiter.check()
    if not ok:
        raise RuntimeError(f"Rate limit: wait {wait:.1f}s before next yfinance call")

Design notes
------------
* Pure Python, zero extra dependencies.
* Thread-safe via threading.Lock (Streamlit spawns one thread per session).
* Does NOT persist across process restarts (Streamlit Cloud recycles workers);
  that is intentional — the SQLite cache layer already handles cold-start.
* The limiter is a soft guard: it raises RuntimeError so callers can
  surface a friendly st.warning instead of letting Yahoo return HTTP 429.
"""
from __future__ import annotations

import threading
import time
from collections import deque

from utils.logger import get_logger

log = get_logger(__name__)


class RateLimiter:
    """Sliding-window rate limiter.

    Parameters
    ----------
    max_calls : int
        Maximum number of calls allowed inside *window_s* seconds.
    window_s  : float
        Duration of the sliding window in seconds.
    name      : str
        Human-readable name used in log messages.
    """

    def __init__(self, max_calls: int, window_s: float, name: str = "default") -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be >= 1")
        if window_s <= 0:
            raise ValueError("window_s must be > 0")
        self.max_calls = max_calls
        self.window_s  = window_s
        self.name      = name
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self) -> tuple[bool, float]:
        """Return ``(allowed, seconds_to_wait)``.

        ``allowed`` is True when the call fits inside the current window.
        ``seconds_to_wait`` is 0.0 when allowed; otherwise the number of
        seconds until the oldest call expires out of the window.
        """
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            if len(self._calls) < self.max_calls:
                self._calls.append(now)
                return True, 0.0
            # Window is full — calculate wait time
            oldest    = self._calls[0]
            wait_secs = self.window_s - (now - oldest)
            log.warning(
                "RateLimiter[%s]: limit reached (%d/%d in %.0fs window), "
                "caller must wait %.1fs",
                self.name, len(self._calls), self.max_calls, self.window_s, wait_secs,
            )
            return False, max(wait_secs, 0.0)

    def wait_and_call(self) -> None:
        """Block until the call is allowed, then register it.

        Use only in non-Streamlit contexts (background threads, CLI)
        where blocking is acceptable.  In Streamlit, prefer :meth:`check`
        and surface the wait as a user-facing message.
        """
        while True:
            ok, wait = self.check()
            if ok:
                return
            log.debug("RateLimiter[%s]: sleeping %.1fs", self.name, wait)
            time.sleep(wait)

    def reset(self) -> None:
        """Clear all recorded call timestamps (useful in tests)."""
        with self._lock:
            self._calls.clear()

    @property
    def current_count(self) -> int:
        """Number of calls recorded in the current window (thread-safe snapshot)."""
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            return len(self._calls)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evict(self, now: float) -> None:
        """Remove timestamps that have slipped outside the sliding window."""
        cutoff = now - self.window_s
        while self._calls and self._calls[0] < cutoff:
            self._calls.popleft()

    def __repr__(self) -> str:
        return (
            f"RateLimiter(name={self.name!r}, max_calls={self.max_calls}, "
            f"window_s={self.window_s}, current={self.current_count})"
        )


# ---------------------------------------------------------------------------
# Module-level singleton limiters
# ---------------------------------------------------------------------------
# These are shared across ALL Streamlit sessions within one worker process.
# Streamlit Community Cloud runs a single worker process, so this correctly
# enforces a process-wide cap regardless of how many browser tabs are open.

# yfinance: Yahoo Finance undocumented limit is ~60 req/min per IP.
# We cap at 30/min (generous headroom) to avoid HTTP 429 cascades.
yfinance_limiter: RateLimiter = RateLimiter(
    max_calls=30,
    window_s=60.0,
    name="yfinance",
)

# SMTP: avoid accidental email storms from alert loops.
# 10 emails per 5 minutes per process is generous for a personal tracker.
smtp_limiter: RateLimiter = RateLimiter(
    max_calls=10,
    window_s=300.0,
    name="smtp",
)

# SMS/Twilio: Twilio free-tier is rate-limited; keep bursts minimal.
twilio_limiter: RateLimiter = RateLimiter(
    max_calls=5,
    window_s=300.0,
    name="twilio",
)
