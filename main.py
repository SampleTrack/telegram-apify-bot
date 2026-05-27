import asyncio
import logging
import os
import signal
import sys

sys.stdout.reconfigure(line_buffering=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def validate():
    import config
    missing = []
    if not config.API_ID:      missing.append("API_ID")
    if not config.API_HASH:    missing.append("API_HASH")
    if not config.BOT_TOKEN:   missing.append("BOT_TOKEN")
    if not config.CHANNEL_ID:  missing.append("CHANNEL_ID")
    if not config.APIFY_TOKEN: missing.append("APIFY_TOKEN")
    if missing:
        logger.error(f"❌ Missing env vars: {', '.join(missing)}")
        sys.exit(1)
    logger.info("✅ Config OK")


async def main():
    validate()

    from bot.health import start_health_server
    from bot.scheduler.jobs import setup_scheduler
    from pyrogram import Client
    import config

    port = int(os.getenv("PORT", 8000))
    health = await start_health_server(port)

    app = Client(
        name="auto_post_bot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
    )

    async with app:
        logger.info("✅ Bot connected to Telegram")
        scheduler = setup_scheduler(app)

        stop = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                asyncio.get_event_loop().add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass

        logger.info("🤖 Auto-post bot is running!")
        await stop.wait()

        scheduler.shutdown(wait=False)
        await health.cleanup()
        logger.info("👋 Stopped.")


if __name__ == "__main__":
    asyncio.run(main())
