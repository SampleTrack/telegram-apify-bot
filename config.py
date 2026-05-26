import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Your Telegram channel username or ID (e.g. "@mydeals" or -100xxxxxxxxxx)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# Bot owner's Telegram user ID (for admin commands)
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# ── Apify ─────────────────────────────────────────────────
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")

# Free Amazon scraper Actor on Apify Store
AMAZON_ACTOR_ID = "junglee/free-amazon-product-scraper"

# How many products to fetch per Apify run (keep low on free plan)
MAX_RESULTS = int(os.getenv("MAX_RESULTS", 5))

# ── MongoDB ───────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "apify_bot")

# ── Redis ─────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# How long to cache Apify results (seconds) — saves credits
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # 1 hour

# ── Scheduler ─────────────────────────────────────────────
# How often to auto-post deals to channel (in hours)
AUTO_POST_INTERVAL_HOURS = int(os.getenv("AUTO_POST_INTERVAL_HOURS", 6))

# Keywords to search for deals automatically
DEFAULT_DEAL_KEYWORDS = os.getenv(
    "DEFAULT_DEAL_KEYWORDS",
    "smartphone deals,earbuds offer,smartwatch sale"
).split(",")

# Minimum discount % to consider a product a "deal"
MIN_DISCOUNT_PERCENT = int(os.getenv("MIN_DISCOUNT_PERCENT", 10))
