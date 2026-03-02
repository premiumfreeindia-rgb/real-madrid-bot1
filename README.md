# 👑 Real Madrid Zone — Telegram News Bot

Automated Real Madrid news bot that:
- Scrapes latest Real Madrid news from multiple RSS feeds
- Generates an **anime-styled** image using Pollinations.ai (free, no key)
- Creates a **premium branded post** with gold/dark Real Madrid theme
- Sends it to your Telegram chat automatically every **30 minutes**
- Runs 100% free on **GitHub Actions**

---

## 🚀 Setup (One-Time, ~5 minutes)

### Step 1 — Create GitHub Repository

1. Go to [github.com](https://github.com) → **New Repository**
2. Name it: `real-madrid-bot`
3. Set to **Private**
4. Click **Create repository**

### Step 2 — Upload Files

Upload all files from this folder to your repository:
```
real-madrid-bot/
├── .github/
│   └── workflows/
│       └── bot.yml
├── src/
│   └── bot.py
├── requirements.txt
└── README.md
```

### Step 3 — Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `TELEGRAM_TOKEN` | `8627795096:AAER3rfLzA7KCnRWduEvbxvERmulTVtB-eE` |
| `TELEGRAM_CHAT_ID` | `5233860632` |
| `GNEWS_KEY` | *(leave empty for now, optional)* |

### Step 4 — Add GitHub PAT (for saving state)

1. Go to GitHub → **Settings** (your profile) → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name: `real-madrid-bot`
4. Expiration: **No expiration**
5. Check: `repo` (full control)
6. Click **Generate token** → Copy it
7. Go back to repo → **Settings** → **Secrets** → Add secret:
   - Name: `GH_PAT`
   - Value: *(paste your token)*

### Step 5 — Enable GitHub Actions

1. Go to your repo → **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. Click on **"Real Madrid Bot"** → **"Run workflow"** → **"Run workflow"**

✅ **That's it!** The bot will now run every 30 minutes automatically.

---

## 🧪 Test Locally

```bash
pip install -r requirements.txt
python src/bot.py
```

---

## 📸 What the Post Looks Like

- **Dark premium background** with anime-generated football scene
- **Gold Real Madrid branding** (header, footer, accent lines)
- **Bold white headline** with shadow
- **Key bullet points** from the article
- **Hashtags**: #RealMadrid #HalaMadrid #UCL #LaLiga
- **Source + read more link** in Telegram caption

---

## ⚙️ Customization

Edit `src/bot.py`:

- `RSS_FEEDS` — add/remove news sources
- `GOLD`, `DARK_BG` — change colors
- Cron in `bot.yml`: `'*/30 * * * *'` = every 30 min, `'0 * * * *'` = every hour

---

## 💡 Notes

- **Pollinations.ai** is used for image generation — completely free, no signup
- Bot only posts **new articles** (tracks sent via `sent_articles.json`)
- **Max 1 post per run** to avoid spam
- GitHub Actions free tier = 2,000 minutes/month (30min runs ≈ 1,440 min/month = fine)
