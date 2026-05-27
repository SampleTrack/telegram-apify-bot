import asyncio
import logging
import httpx
from config import APIFY_TOKEN, AMAZON_ACTOR_ID, MAX_RESULTS

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
HEADERS = {"Authorization": f"Bearer {APIFY_TOKEN}"}


async def _wait_for_run(run_id: str, timeout: int = 120) -> bool:
    """Poll Apify until the Actor run finishes or times out."""
    url = f"{APIFY_BASE}/actor-runs/{run_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(timeout // 5):
            await asyncio.sleep(5)
            resp = await client.get(url, headers=HEADERS)
            status = resp.json().get("data", {}).get("status", "")
            if status == "SUCCEEDED":
                return True
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                logger.error(f"Apify run {run_id} ended with status: {status}")
                return False
    logger.error(f"Apify run {run_id} timed out after {timeout}s")
    return False


async def search_amazon(keyword: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """
    Trigger the Amazon scraper Actor and return product list.
    Returns empty list on failure.
    """
    logger.info(f"Starting Apify Amazon search: '{keyword}'")

    # Convert keyword to Amazon India search URL
    import urllib.parse
    search_url = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(keyword)}"

    payload = {
        "categoryUrls": [{"url": search_url}],
        "maxItems": max_results,
        "useStealth": False,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Start Actor run — note: actor ID uses ~ not / in URL
        actor_url_id = AMAZON_ACTOR_ID.replace("/", "~")
        resp = await client.post(
            f"{APIFY_BASE}/acts/{actor_url_id}/runs",
            headers=HEADERS,
            json=payload,
        )
        if resp.status_code not in (200, 201):
            logger.error(f"Failed to start Apify run: {resp.text}")
            return []

        run_id = resp.json()["data"]["id"]
        logger.info(f"Apify run started: {run_id}")

    # Wait for completion
    success = await _wait_for_run(run_id)
    if not success:
        return []

    # Fetch results
    async with httpx.AsyncClient(timeout=30) as client:
        result = await client.get(
            f"{APIFY_BASE}/actor-runs/{run_id}/dataset/items",
            headers=HEADERS,
            params={"limit": max_results},
        )
        if result.status_code != 200:
            logger.error(f"Failed to fetch Apify results: {result.text}")
            return []

        items = result.json()
        logger.info(f"Apify returned {len(items)} items for '{keyword}'")
        return items


def _extract_price(raw_val) -> float:
    """Handle price as dict {'value': 1499, 'currency': ''} or plain string/number."""
    if raw_val is None:
        return 0.0
    if isinstance(raw_val, dict):
        return float(raw_val.get("value") or raw_val.get("amount") or 0)
    if isinstance(raw_val, (int, float)):
        return float(raw_val)
    # String — strip currency symbols
    cleaned = str(raw_val).replace("₹", "").replace(",", "").replace("$", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_product(raw: dict) -> dict | None:
    """Normalize raw Apify Amazon data into a clean product dict."""
    try:
        title = raw.get("title") or raw.get("name") or ""

        price = _extract_price(
            raw.get("price") or raw.get("currentPrice") or raw.get("salePrice")
        )
        original = _extract_price(
            raw.get("originalPrice") or raw.get("listPrice") or raw.get("mrp") or price
        )

        discount = 0
        if original > 0 and price < original:
            discount = round(((original - price) / original) * 100)

        return {
            "title": title[:100],
            "price": price,
            "original_price": original,
            "discount": discount,
            "rating": raw.get("stars") or raw.get("rating") or "N/A",
            "reviews": raw.get("reviewsCount") or raw.get("reviews") or 0,
            "url": raw.get("url") or raw.get("link") or "",
            "image": raw.get("thumbnailImage") or raw.get("image") or "",
            "asin": raw.get("asin") or "",
        }
    except Exception as e:
        logger.warning(f"Failed to parse product: {e}")
        return None


async def get_deals(keyword: str, min_discount: int = 10) -> list[dict]:
    """Search Amazon and return only products with discount >= min_discount%."""
    raw_items = await search_amazon(keyword)
    products = []
    for raw in raw_items:
        product = parse_product(raw)
        if product and product["discount"] >= min_discount:
            products.append(product)
    return products
