import asyncio
import logging
import urllib.parse
import httpx
from config import APIFY_TOKEN, ACTOR_ID, MAX_RESULTS, MIN_DISCOUNT

logger = logging.getLogger(__name__)
BASE   = "https://api.apify.com/v2"
HDRS   = {"Authorization": f"Bearer {APIFY_TOKEN}"}


def _to_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, dict):
        return float(val.get("value") or val.get("amount") or 0)
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = str(val).replace("₹","").replace(",","").replace("$","").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse(raw: dict) -> dict | None:
    try:
        price    = _to_float(raw.get("price") or raw.get("currentPrice"))
        original = _to_float(raw.get("originalPrice") or raw.get("listPrice") or price)
        discount = round((original - price) / original * 100) if original > price else 0
        return {
            "title"    : (raw.get("title") or raw.get("name") or "")[:100],
            "price"    : price,
            "original" : original,
            "discount" : discount,
            "rating"   : raw.get("stars") or raw.get("rating") or "N/A",
            "reviews"  : raw.get("reviewsCount") or raw.get("reviews") or 0,
            "url"      : raw.get("url") or raw.get("link") or "",
            "asin"     : raw.get("asin") or "",
        }
    except Exception as e:
        logger.debug(f"Parse skip: {e}")
        return None


async def _wait(run_id: str, timeout: int = 120) -> bool:
    url = f"{BASE}/actor-runs/{run_id}"
    async with httpx.AsyncClient(timeout=30) as c:
        for _ in range(timeout // 5):
            await asyncio.sleep(5)
            r = await c.get(url, headers=HDRS)
            status = r.json().get("data", {}).get("status", "")
            if status == "SUCCEEDED":
                return True
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                return False
    return False


async def fetch_deals(keyword: str) -> list[dict]:
    """Fetch Amazon deals for a keyword and return parsed products with discount >= MIN_DISCOUNT."""
    search_url = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(keyword)}"
    actor_id   = ACTOR_ID.replace("/", "~")

    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.post(
            f"{BASE}/acts/{actor_id}/runs",
            headers=HDRS,
            json={"categoryUrls": [{"url": search_url}], "maxItems": MAX_RESULTS},
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Apify start failed for '{keyword}': {resp.text[:200]}")
            return []
        run_id = resp.json()["data"]["id"]

    logger.info(f"Apify run {run_id} started for '{keyword}'")

    if not await _wait(run_id):
        logger.warning(f"Run {run_id} timed out for '{keyword}'")
        return []

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            f"{BASE}/actor-runs/{run_id}/dataset/items",
            headers=HDRS,
            params={"limit": MAX_RESULTS},
        )
        items = r.json() if r.status_code == 200 else []

    products = [p for p in (_parse(i) for i in items) if p and p["discount"] >= MIN_DISCOUNT]
    logger.info(f"'{keyword}' → {len(products)} deals found")
    return products
