import logging
from pyrogram import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import CHANNEL_ID, KEYWORDS, MORNING_HOUR, EVENING_HOUR
from bot.services.scraper import fetch_deals
from bot.services.formatter import morning_post, evening_post, flash_post

logger = logging.getLogger(__name__)


async def _send(client: Client, text: str):
    if not text or not CHANNEL_ID:
        return
    try:
        await client.send_message(CHANNEL_ID, text, disable_web_page_preview=False)
        logger.info("✅ Message sent to channel")
    except Exception as e:
        logger.error(f"Send failed: {e}")


async def run_morning_post(client: Client):
    """9 AM IST — post deals per keyword + flash alert if 40%+ found."""
    logger.info("🌅 Running morning post...")
    all_deals = []

    for kw in KEYWORDS:
        try:
            deals = await fetch_deals(kw)
            if deals:
                text = morning_post(kw, deals)
                await _send(client, text)
                all_deals.extend(deals)
        except Exception as e:
            logger.error(f"Morning post failed for '{kw}': {e}")

    # Flash sale post if any hot deals
    if all_deals:
        flash = flash_post(all_deals)
        if flash:
            await _send(client, flash)


async def run_evening_post(client: Client):
    """8 PM IST — best of the day summary."""
    logger.info("🌙 Running evening summary...")
    all_deals = []

    for kw in KEYWORDS:
        try:
            deals = await fetch_deals(kw)
            all_deals.extend(deals)
        except Exception as e:
            logger.error(f"Evening fetch failed for '{kw}': {e}")

    text = evening_post(all_deals)
    await _send(client, text)


async def run_manual_post(client: Client):
    """Triggered by /postdeals admin command."""
    await run_morning_post(client)


def setup_scheduler(app: Client) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        run_morning_post, "cron",
        hour=MORNING_HOUR, minute=0,
        args=[app], id="morning",
        misfire_grace_time=600,
    )
    scheduler.add_job(
        run_evening_post, "cron",
        hour=EVENING_HOUR, minute=0,
        args=[app], id="evening",
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info(
        f"✅ Scheduler ready\n"
        f"   🌅 Morning post → {MORNING_HOUR}:00 AM IST\n"
        f"   🌙 Evening post → {EVENING_HOUR}:00 PM IST"
    )
    return scheduler
