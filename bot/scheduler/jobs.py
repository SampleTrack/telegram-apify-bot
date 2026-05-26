import logging
from pyrogram import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import (
    CHANNEL_ID,
    AUTO_POST_INTERVAL_HOURS,
    DEFAULT_DEAL_KEYWORDS,
    MIN_DISCOUNT_PERCENT,
)
from bot.services.apify import get_deals
from bot.services.formatter import (
    deal_channel_post,
    best_deals_summary,
    score_deal,
    price_drop_alert,
)
from bot.db.mongo import (
    get_all_tracked,
    update_tracked_price,
    is_deal_posted,
    mark_deal_posted,
)
from bot.services.apify import search_amazon, parse_product

logger = logging.getLogger(__name__)


def _filter_new_deals(products: list[dict], min_discount: int) -> list[dict]:
    """Remove already-posted deals and below-threshold discounts."""
    return [
        p for p in products
        if p.get("discount", 0) >= min_discount and p.get("asin")
    ]


async def _deduplicate(products: list[dict]) -> list[dict]:
    """Remove ASINs posted in the last 48 hours."""
    fresh = []
    for p in products:
        asin = p.get("asin", "")
        if asin and not await is_deal_posted(asin, hours=48):
            fresh.append(p)
    return fresh


async def post_deals_to_channel(client: Client):
    """
    Fetch deals for all keywords, score them, deduplicate,
    and post the best ones to your Telegram channel.
    """
    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID not set — skipping auto-post")
        return

    logger.info(f"⏰ Auto-posting best deals to {CHANNEL_ID}")

    all_fresh_deals: list[dict] = []

    # Step 1: Collect deals from all keywords
    for keyword in DEFAULT_DEAL_KEYWORDS:
        keyword = keyword.strip()
        try:
            products = await get_deals(keyword, MIN_DISCOUNT_PERCENT)
            fresh = _filter_new_deals(products, MIN_DISCOUNT_PERCENT)
            fresh = await _deduplicate(fresh)

            if fresh:
                # Sort by score (best first) and post per-keyword
                fresh.sort(key=score_deal, reverse=True)
                all_fresh_deals.extend(fresh)

                text = deal_channel_post(keyword, fresh)
                if text:
                    await client.send_message(
                        CHANNEL_ID,
                        text,
                        disable_web_page_preview=False,
                    )
                    # Mark all posted deals
                    for p in fresh[:5]:
                        await mark_deal_posted(
                            p.get("asin", ""),
                            p.get("title", ""),
                            p.get("price", 0),
                            p.get("discount", 0),
                        )
                    logger.info(f"✅ Posted {len(fresh[:5])} deals for '{keyword}'")
            else:
                logger.info(f"No new deals for '{keyword}' (all already posted or no discount)")

        except Exception as e:
            logger.error(f"Failed to process keyword '{keyword}': {e}")

    # Step 2: Post a "Best of the bunch" summary if we have enough deals
    if len(all_fresh_deals) >= 3:
        try:
            summary = best_deals_summary(all_fresh_deals, top_n=3)
            if summary:
                await client.send_message(
                    CHANNEL_ID,
                    f"━━━━━━━━━━━━━━━━━━━\n{summary}",
                    disable_web_page_preview=False,
                )
                logger.info("✅ Posted 'Best Deals' summary")
        except Exception as e:
            logger.error(f"Failed to post summary: {e}")


async def check_price_drops(client: Client):
    """
    Check all tracked products for price drops and alert users.
    Runs every 12 hours.
    """
    logger.info("🔍 Checking price drops for tracked products...")

    tracked = await get_all_tracked()
    if not tracked:
        return

    seen_asins: dict[str, float] = {}

    for item in tracked:
        asin = item.get("asin", "")
        user_id = item.get("user_id")
        old_price = item.get("last_price", 0)

        if not asin or not user_id:
            continue

        if asin not in seen_asins:
            try:
                raw = await search_amazon(asin, 1)
                products = [p for p in (parse_product(r) for r in raw) if p]
                if products:
                    seen_asins[asin] = products[0]["price"]
                    await update_tracked_price(asin, products[0]["price"])
            except Exception as e:
                logger.error(f"Price check failed for ASIN {asin}: {e}")
                continue

        new_price = seen_asins.get(asin)
        if new_price is None:
            continue

        if old_price > 0 and new_price < old_price:
            drop_pct = ((old_price - new_price) / old_price) * 100
            if drop_pct >= 5:
                try:
                    alert_text = price_drop_alert(item, old_price, new_price)
                    await client.send_message(user_id, alert_text)
                    logger.info(f"🚨 Sent price drop alert to {user_id} for ASIN {asin}")
                except Exception as e:
                    logger.warning(f"Failed to send alert to {user_id}: {e}")


def setup_scheduler(app: Client) -> AsyncIOScheduler:
    """Create and start the APScheduler with all jobs."""
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # Auto-post deals to channel
    scheduler.add_job(
        post_deals_to_channel,
        trigger="interval",
        hours=AUTO_POST_INTERVAL_HOURS,
        args=[app],
        id="auto_post_deals",
        name="Auto Post Best Deals",
        misfire_grace_time=300,
    )

    # Check price drops
    scheduler.add_job(
        check_price_drops,
        trigger="interval",
        hours=12,
        args=[app],
        id="check_price_drops",
        name="Price Drop Checker",
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info(
        f"✅ Scheduler started "
        f"(deals every {AUTO_POST_INTERVAL_HOURS}h | price checks every 12h)"
    )
    return scheduler
