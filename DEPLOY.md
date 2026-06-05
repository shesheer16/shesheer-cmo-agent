# Shesheer CMO Agent — Deployment Guide

## Architecture
- **Telegram Bot + Health API** → Render.com (free tier, Singapore region)
- **Streamlit Web UI** → Streamlit Community Cloud (free)
- **Database** → SQLite (`data/memory.db`) + ChromaDB (`data/chromadb/`) on Render ephemeral disk

---

## 1. Deploy to Render.com

### Step 1 — Create Render Account
Go to [render.com](https://render.com) → Sign up with GitHub (no credit card needed for free tier)

### Step 2 — Connect Repository
- New → Web Service
- Connect your GitHub repo: `shesheer-cmo-agent`
- Branch: `main`

### Step 3 — Configure Service
| Setting | Value |
|---|---|
| Name | `shesheer-cmo-agent` |
| Region | Singapore |
| Runtime | Python 3 |
| Build Command | `pip install uv && uv sync --frozen` |
| Start Command | `python main.py --bot` |
| Plan | Free |

### Step 4 — Set Environment Variables
In Render Dashboard → Environment → Add the following:

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key |
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `TELEGRAM_ALLOWED_USER_ID` | Your Telegram numeric user ID |
| `SENTRY_DSN` | *(optional — leave blank to skip)* |
| `PYTHONUNBUFFERED` | `1` |

### Step 5 — Health Check
Render will automatically ping `https://your-app.onrender.com/health`
Expected response: `{"status": "ok", ...}`

### Step 6 — Keep Alive (Prevent Sleep)
Render free tier sleeps after 15 min inactivity.
Set up [BetterUptime](https://betteruptime.com) (free) to ping `/health` every 10 minutes.

---

## 2. Deploy Streamlit UI

### Step 1 — Go to Streamlit Community Cloud
[share.streamlit.io](https://share.streamlit.io) → Sign in with GitHub

### Step 2 — New App
- Repository: `shesheer-cmo-agent`
- Branch: `main`
- Main file path: `streamlit_app.py`

### Step 3 — Set Secrets
In Streamlit Cloud → App Settings → Secrets:
```toml
GEMINI_API_KEY = "your-key-here"
APP_PASSWORD = "your-chosen-password"
```

---

## 3. Local Development

```bash
# Run health checks
uv run python main.py --health

# Start bot + health server locally
uv run python main.py --bot

# Run Streamlit UI
uv run streamlit run streamlit_app.py

# Test /health endpoint
curl http://localhost:8000/health
```

---

## 4. Weekly Report
Every Sunday at 2am, the agent sends a Telegram message with:
- Conversations count
- Total cost (₹)
- Knowledge base chunk count
- System health status

## 5. Rollback
```bash
git revert HEAD
git push
# Render auto-deploys the reverted commit
```

---

## Current Status
- Telegram: `t.me/your_bot_username` *(set after Telegram bot is live)*
- Streamlit: `your-app.streamlit.app` *(set after Streamlit deploy)*
- Health: `https://your-app.onrender.com/health`
