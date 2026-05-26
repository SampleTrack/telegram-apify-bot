import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


def get_db():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client[DB_NAME]


# ── Collections ───────────────────────────────────────────

def tracked_col():
    return get_db()["tracked_products"]


def history_col():
    return get_db()["search_history"]


def settings_col():
    return get_db()["settings"]


def posted_deals_col():
    return get_db()["posted_deals"]


# ── Tracked Products (price tracking) ────────────────────

async def add_tracked_product(user_id: int, product: dict) -> bool:
    """Track a product for price drop alerts."""
    try:
        col = tracked_col()
        await col.update_one(
            {"user_id": user_id, "asin": product["asin"]},
            {
                "$set": {
                    "user_id": user_id,
                    "asin": product["asin"],
                    "title": product["title"],
                    "url": product["url"],
                    "target_price": product["price"],
                    "last_price": product["price"],
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"add_tracked_product error: {e}")
        return False


async def get_user_tracked(user_id: int) -> list[dict]:
    """Get all products tracked by a user."""
    try:
        col = tracked_col()
        cursor = col.find({"user_id": user_id})
        return await cursor.to_list(length=20)
    except Exception as e:
        logger.error(f"get_user_tracked error: {e}")
        return []


async def get_all_tracked() -> list[dict]:
    """Get all tracked products (for scheduler to check prices)."""
    try:
        col = tracked_col()
        cursor = col.find({})
        return await cursor.to_list(length=500)
    except Exception as e:
        logger.error(f"get_all_tracked error: {e}")
        return []


async def update_tracked_price(asin: str, new_price: float):
    """Update stored price after a price check."""
    try:
        await tracked_col().update_one(
            {"asin": asin},
            {"$set": {"last_price": new_price, "updated_at": datetime.utcnow()}},
        )
    except Exception as e:
        logger.error(f"update_tracked_price error: {e}")


async def remove_tracked_product(user_id: int, asin: str) -> bool:
    try:
        result = await tracked_col().delete_one({"user_id": user_id, "asin": asin})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"remove_tracked_product error: {e}")
        return False


# ── Search History ────────────────────────────────────────

async def log_search(user_id: int, keyword: str, result_count: int):
    """Save search history entry."""
    try:
        await history_col().insert_one(
            {
                "user_id": user_id,
                "keyword": keyword,
                "result_count": result_count,
                "timestamp": datetime.utcnow(),
            }
        )
    except Exception as e:
        logger.error(f"log_search error: {e}")


# ── Bot Settings ──────────────────────────────────────────

async def get_setting(key: str, default=None):
    try:
        doc = await settings_col().find_one({"key": key})
        return doc["value"] if doc else default
    except Exception as e:
        logger.error(f"get_setting error: {e}")
        return default


async def set_setting(key: str, value):
    try:
        await settings_col().update_one(
            {"key": key},
            {"$set": {"key": key, "value": value, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"set_setting error: {e}")


# ── Posted Deals (deduplication) ─────────────────────────

async def is_deal_posted(asin: str, hours: int = 48) -> bool:
    """Check if this ASIN was already posted in the last N hours."""
    from datetime import timedelta
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        doc = await posted_deals_col().find_one({
            "asin": asin,
            "posted_at": {"$gte": cutoff}
        })
        return doc is not None
    except Exception as e:
        logger.error(f"is_deal_posted error: {e}")
        return False


async def mark_deal_posted(asin: str, title: str, price: float, discount: int):
    """Record that a deal was posted to the channel."""
    try:
        await posted_deals_col().insert_one({
            "asin": asin,
            "title": title,
            "price": price,
            "discount": discount,
            "posted_at": datetime.utcnow(),
        })
    except Exception as e:
        logger.error(f"mark_deal_posted error: {e}")


async def get_recent_posted_deals(limit: int = 20) -> list[dict]:
    """Get recently posted deals (for /recentdeals admin command)."""
    try:
        cursor = posted_deals_col().find({}).sort("posted_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        logger.error(f"get_recent_posted_deals error: {e}")
        return []
