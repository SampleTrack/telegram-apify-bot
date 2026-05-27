import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
API_ID        = int(os.getenv("API_ID", 0))
API_HASH      = os.getenv("API_HASH", "")
BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
CHANNEL_ID    = os.getenv("CHANNEL_ID", "")   # e.g. @mychannel or -100xxxxxxx

# Apify
APIFY_TOKEN   = os.getenv("APIFY_TOKEN", "")
ACTOR_ID      = "junglee/free-amazon-product-scraper"
MAX_RESULTS   = int(os.getenv("MAX_RESULTS", 5))

# Deal filter
MIN_DISCOUNT  = int(os.getenv("MIN_DISCOUNT", 10))   # minimum % to qualify as deal

# Keywords — comma separated
KEYWORDS      = [k.strip() for k in os.getenv(
    "KEYWORDS",
    "smartphone deals,earbuds offer,smartwatch sale,laptop offer,camera deals"
).split(",")]

# Post times (IST 24h format)
MORNING_HOUR  = int(os.getenv("MORNING_HOUR", 9))    # 9 AM
EVENING_HOUR  = int(os.getenv("EVENING_HOUR", 20))   # 8 PM
