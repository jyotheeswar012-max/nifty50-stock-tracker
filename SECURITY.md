# Security Policy

## Responsible Disclosure

If you discover a security vulnerability in this project, **please do not open a public GitHub issue**.
Instead, email the maintainer directly (see the GitHub profile for contact details) with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact

We aim to respond within **72 hours** and will coordinate a fix before public disclosure.

---

## Secret Management

This app uses three categories of secrets. **None of them should ever be committed to git.**

| Secret | Where it lives | How the code reads it |
|--------|---------------|----------------------|
| Firebase Web API Key | `.streamlit/secrets.toml` → `[firebase] api_key` | `st.secrets["firebase"]["api_key"]` |
| SMTP credentials | `.streamlit/secrets.toml` → `[smtp]` | `st.secrets["smtp"]` |
| Twilio credentials | `.streamlit/secrets.toml` → `[twilio]` | `st.secrets["twilio"]` |
| Supabase keys | `.streamlit/secrets.toml` → `[supabase]` | `st.secrets["supabase"]` |

### Local development

```bash
# 1. Copy the template
cp .streamlit/secrets.toml.template .streamlit/secrets.toml

# 2. Fill in real values
nano .streamlit/secrets.toml          # or your preferred editor

# 3. Verify it is git-ignored
git status .streamlit/secrets.toml    # should NOT appear
```

> `secrets.toml` is listed in `.gitignore` — a `git status` check is still recommended before every commit.

### Streamlit Community Cloud

Paste the **contents of `secrets.toml`** (with real values) into:
> App dashboard → **⋮** → Settings → **Secrets**

Do **not** upload the file directly — use the secrets text box.

### Self-hosted / Docker

Set each key as an environment variable prefixed with `STREAMLIT__`:

```bash
export STREAMLIT__FIREBASE__API_KEY="AIzaSy..."
export STREAMLIT__SMTP__PASSWORD="your-app-password"
export STREAMLIT__TWILIO__TOKEN="your-auth-token"
```

---

## Rate Limiting

`utils/rate_limit.py` provides a thread-safe sliding-window `RateLimiter` class with
three pre-configured module-level singletons:

| Limiter | Cap | Window | Rationale |
|---------|-----|--------|-----------|
| `yfinance_limiter` | 30 calls | 60 s | Yahoo Finance ~60 req/min per IP; we use half to leave headroom |
| `smtp_limiter` | 10 emails | 300 s | Prevents alert storms from runaway loops |
| `twilio_limiter` | 5 SMS | 300 s | Twilio free-tier is strict; keeps costs bounded |

Import and use in fetch/notification helpers:

```python
from utils.rate_limit import yfinance_limiter

ok, wait = yfinance_limiter.check()
if not ok:
    st.warning(f"⚠️ Rate limit reached. Retry in {wait:.0f}s.")
    return
```

---

## What is and is not in this repo

| ✅ Safe to commit | ❌ Never commit |
|------------------|----------------|
| `.streamlit/secrets.toml.template` | `.streamlit/secrets.toml` |
| `utils/rate_limit.py` | `serviceAccountKey.json` |
| `SECURITY.md` | `*.pem`, `*.key`, `*.p12` |
| Source code | `.env`, `.env.*`, `*.env` |
| `requirements.txt` | Any file containing passwords or tokens |

---

## Dependency Security

Run `pip audit` (or `safety check`) regularly to check for known CVEs in dependencies:

```bash
pip install pip-audit
pip-audit -r requirements.txt
```

Dependabot alerts are enabled on this repository.
