import asyncio
import logging
import os
import signal
import sys

# Force unbuffered output so Render shows logs immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from bot.health import start_health_server

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)

logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


def validate_config():
    """Check all required env vars are set before starting."""
    import config
    errors = []

    if not config.API_ID:
        errors.append("API_ID is missing or 0")
    if not config.API_HASH:
        errors.append("API_HASH is missing")
    if not config.BOT_TOKEN:
        errors.append("BOT_TOKEN is missing")
    if not config.APIFY_TOKEN:
        errors.append("APIFY_TOKEN is missing")
    if not config.MONGO_URI or config.MONGO_URI == "mongodb://localhost:27017":
        errors.append("MONGO_URI is not set (still default)")
    if not config.REDIS_URL or config.REDIS_URL == "redis://localhost:6379":
        errors.append("REDIS_URL is not set (still default)")

    if errors:
        logger.error("❌ Missing environment variables:")
        for e in errors:
            logger.error(f"   • {e}")
        logger.error("👉 Add these in Render → Environment tab")
        sys.exit(1)

    logger.info("✅ All environment variables loaded")


async def main():
    logger.info("🚀 Starting Apify Deal Bot...")

    # Validate config first
    validate_config()

    # Start health server
    port = int(os.getenv("PORT", 8000))
    health_runner = await start_health_server(port)

    # Import after validation to catch errors clearly
    try:
        from bot.client import create_client
        from bot.handlers.commands import register_handlers
        from bot.scheduler.jobs import setup_scheduler
    except Exception as e:
        logger.error(f"❌ Import error: {e}", exc_info=True)
        sys.exit(1)

    app = create_client()
    register_handlers(app)

    try:
        async with app:
            logger.info("✅ Bot connected to Telegram")
            scheduler = setup_scheduler(app)

            stop_event = asyncio.Event()

            def _stop(*_):
                logger.info("🛑 Shutdown signal received")
                stop_event.set()

            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    asyncio.get_event_loop().add_signal_handler(sig, _stop)
                except NotImplementedError:
                    pass

            logger.info("🤖 Bot is running!")
            await stop_event.wait()

            scheduler.shutdown(wait=False)
            await health_runner.cleanup()
            logger.info("👋 Bot stopped cleanly.")

    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
