# Configuration

## Environment Variables

Create a `.env` file in the project root (never commit it):

```bash
# .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

## Streamlit Secrets

For Streamlit Cloud deployment, add secrets via the dashboard or `.streamlit/secrets.toml`:

```toml
# .streamlit/secrets.toml  (gitignored)
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
```

## Key Constants (`utils/constants.py`)

| Constant | Default | Description |
|---|---|---|
| `REFRESH_MS` | `5000` | Auto-refresh interval in milliseconds when market is live |
| `CACHE_TTL` | `60` | Streamlit cache TTL in seconds for price data |
| `NIFTY50` | list | All 50 constituent stocks with symbol, sector, beta |
| `NSE_INDICES` | list | Tracked NSE indices with display name and color |
| `FAMOUS_DATES` | dict | Preset historical dates for the Time Machine tab |

To add a new stock or change the refresh rate, edit `utils/constants.py` directly.

## Deployment on Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and set `app.py` as the entry point
4. Add any secrets under **Settings → Secrets**
5. Click **Deploy**
