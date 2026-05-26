import json
import logging
import redis.asyncio as aioredis
from config import REDIS_URL, CACHE_TTL

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def cache_get(key: str) -> list | None:
    """Return cached value or None."""
    try:
        r = await get_redis()
        val = await r.get(key)
        if val:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
    return None


async def cache_set(key: str, value: list, ttl: int = CACHE_TTL) -> None:
    """Store value in cache."""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value))
        logger.debug(f"Cache SET: {key} (ttl={ttl}s)")
    except Exception as e:
        logger.warning(f"Redis set error: {e}")


async def cache_delete(key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as e:
        logger.warning(f"Redis delete error: {e}")


def make_key(prefix: str, query: str) -> str:
    """Generate a safe cache key."""
    return f"{prefix}:{query.lower().strip().replace(' ', '_')}"
