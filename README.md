# 🛒 Telegram Amazon Deal Bot (Apify + Pyrogram)

Auto-posts Amazon deals to your Telegram channel, lets users search products, and sends price drop alerts — powered by **Apify** for scraping and **Pyrogram** for the bot.

---

## 📁 Project Structure

```
telegram-apify-bot/
├── bot/
│   ├── handlers/
│   │   └── commands.py      # All bot commands
│   ├── scheduler/
│   │   └── jobs.py          # APScheduler auto-post + price check
│   ├── services/
│   │   ├── apify.py         # Apify API integration
│   │   ├── cache.py         # Redis caching
│   │   └── formatter.py     # Message formatting
│   └── db/
│       └── mongo.py         # MongoDB operations
├── config.py                # All settings from .env
├── main.py                  # Entry point
├── requirements.txt
├── render.yaml              # Render Worker deployment
└── .env.example             # Copy this to .env
```

---

## ⚡ Features

| Feature | Description |
|---|---|
| `/search <keyword>` | Search Amazon products via Apify |
| `/deals <keyword>` | Show only discounted products |
| `/track <ASIN>` | Track product price |
| `/mylist` | List your tracked products |
| `/untrack <ASIN>` | Stop tracking a product |
| Auto deal posts | Posts deals to channel every N hours |
| Price drop alerts | DMs you when a tracked product drops in price |
| Redis caching | Avoids duplicate Apify API calls (saves credits) |

---

## 🚀 Setup

### 1. Clone & install

```bash
git clone https://github.com/yourname/telegram-apify-bot
cd telegram-apify-bot
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in all values in .env
```

You need:
- **Telegram API credentials** → https://my.telegram.org
- **Bot token** → @BotFather on Telegram
- **Apify token** → https://console.apify.com/account/integrations
- **MongoDB URI** → https://mongodb.com/atlas (free tier)
- **Redis URL** → https://upstash.com (free tier)

### 3. Run locally

```bash
python main.py
```

---

## ☁️ Deploy on Render

1. Push code to GitHub
2. Go to https://render.com → New → **Worker** service
3. Connect your GitHub repo
4. Add all environment variables from `.env`
5. Deploy!

> ✅ Worker service = always running, no free-tier sleep issue

---

## 💰 Apify Free Plan Tips

- Free plan gives **$5/month** credits
- Each Amazon search costs roughly **$0.01–0.05**
- Redis caching prevents duplicate calls
- Keep `MAX_RESULTS=5` to save credits
- Run auto-posts every 6h (not hourly) to conserve budget

---

## 🔧 Tech Stack

- **Pyrogram** — Telegram MTProto bot framework
- **Apify** — Amazon product scraping
- **Motor** — Async MongoDB driver
- **Redis (aioredis)** — Search result caching
- **APScheduler** — Scheduled deal posting & price checks
- **httpx** — Async HTTP for Apify API calls
- **Render** — Cloud deployment (Worker service)
