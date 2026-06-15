---
title: Logger
---

# `utils.logger` — Structured Logging

Centralised logging configuration for the entire application. Import `get_logger(__name__)` at the top of any module — the first call configures the root logger; subsequent calls are instant no-ops.

---

## `get_logger(name)`

```python
def get_logger(name: str) -> logging.Logger
```

Returns a child logger under the `nse_tracker` hierarchy.

```python
from utils.logger import get_logger
log = get_logger(__name__)   # e.g. 'nse_tracker.utils.data'

log.info("fetch_ticker called: symbol=%s period=%s", symbol, period)
log.warning("yfinance returned empty data")
log.error("fetch failed: %s", exc, exc_info=True)  # includes full stack trace
```

---

## `read_recent_logs(n)`

```python
def read_recent_logs(n: int = 100) -> list[str]
```

Returns the last `n` non-empty lines from `logs/app.log` as a list of strings. Returns `[]` if the file doesn't exist yet — never raises.

Used by the sidebar **Live Logs** expander in `app.py`.

---

## `log_file_path()`

```python
def log_file_path() -> str
```

Returns the absolute path to the active log file.

---

## Log Format

Every log line follows this format:

```
2026-06-15T22:05:01+0530  INFO      nse_tracker.utils.data:87  |  fetch_ticker called: symbol=RELIANCE.NS period=3mo
```

| Field | Example | Description |
|---|---|---|
| Timestamp | `2026-06-15T22:05:01+0530` | ISO-8601 with timezone offset |
| Level | `INFO` | Padded to 8 chars for alignment |
| Module:Line | `nse_tracker.utils.data:87` | Full dotted module path + line number |
| Message | `fetch_ticker called: ...` | The log message |

---

## Log Levels Used

| Level | Used For |
|---|---|
| `DEBUG` | Per-symbol fetch details, intraday bar counts, chart series info |
| `INFO` | Tab render times, function entry points, batch fetch summaries |
| `WARNING` | Empty data returns, fallback source activations, stale cache served |
| `ERROR` | Exceptions in except blocks — always includes `exc_info=True` for stack trace |

---

## Changing Log Level

```bash
# Terminal
export LOG_LEVEL=DEBUG && streamlit run app.py

# .streamlit/secrets.toml
[general]
LOG_LEVEL = "DEBUG"
```
