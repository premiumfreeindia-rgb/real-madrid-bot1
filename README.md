# 👑 Real Madrid Zone — Telegram News Bot (Render Deploy)

Runs **24/7 on Render** (free) — posts Real Madrid news to Telegram every 30 minutes with anime-styled images.

---

## 🚀 Setup — 3 Steps

### Step 1 — Push to GitHub

1. Create a **new private GitHub repo** (e.g. `real-madrid-bot`)
2. Upload these files:

```
real-madrid-bot/
├── render.yaml
├── requirements.txt
└── src/
    └── bot.py
```

> **Important:** Do NOT put your token in any file. Tokens go in Render dashboard only.

---

### Step 2 — Deploy on Render

1. Go to [render.com](https://render.com) → Sign up free (use GitHub login)
2. Click **New** → **Blueprint**
3. Connect your GitHub repo
4. Render reads `render.yaml` and creates a **Worker** service automatically

---

### Step 3 — Add Secret Environment Variables

Render dashboard → your service → **Environment** tab → Add:

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | your bot token (from @BotFather) |
| `TELEGRAM_CHAT_ID` | your Telegram chat ID |

Click **Save Changes** → bot restarts and goes live!

---

## 🔒 Security — 100% Safe

- Tokens stored **only** in Render's encrypted environment
- Never in code, never in GitHub
- Render masks secrets in all logs automatically
- Repo can be public — nothing sensitive is in the files

---

## ⚙️ Customization

Edit `src/bot.py`:
- `INTERVAL_MINUTES = 30` — change to 60 for hourly
- `RSS_FEEDS` — add/remove sources

Push to GitHub → Render auto-redeploys.

---

## 🆓 Completely Free

Render (free) + Pollinations.ai (free) + RSS (free) + Telegram API (free) = **$0/month**
