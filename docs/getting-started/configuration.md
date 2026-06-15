---
title: Configuration
---

# Configuration

The app is designed to work out-of-the-box with zero configuration. All optional knobs are listed here.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

Set in your shell:

```bash
export LOG_LEVEL=DEBUG
streamlit run app.py
```

Or in `.streamlit/secrets.toml` (never commit this file):

```toml
[general]
LOG_LEVEL = "DEBUG"
```

---

## Streamlit Configuration

The `.streamlit/config.toml` file controls Streamlit UI behaviour:

```toml
[theme]
base = "dark"
primaryColor = "#009688"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1e2530"
textColor = "#fafafa"

[server]
headless = true
port = 8501
```

---

## Cache TTL

Cache time-to-live is set in `utils/constants.py`:

```python
CACHE_TTL = 30      # seconds — live price cache during market hours
```

The Time Machine history fetch has a separate TTL of 3600 seconds (1 hour) since historical data never changes.

---

## Data Source Priority

The fallback order is hard-coded in `utils/data.py` and cannot be changed via config:

```
1. Yahoo Finance (yfinance)   — always attempted first
2. NSE India (nselib)         — attempted if yfinance returns empty
3. Stale in-memory cache      — served with a visible warning if both live sources fail
```

To disable the nselib fallback entirely, simply do not install the `nselib` package.

---

## Google Analytics

The `mkdocs.yml` includes a placeholder for Google Analytics:

```yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX
```

Replace `G-XXXXXXXXXX` with your actual Measurement ID to enable analytics on the docs site.
