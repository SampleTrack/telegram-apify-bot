import asyncio
import logging
import os
import signal
import sys

from bot.client import create_client
from bot.handlers.commands import register_handlers
from bot.scheduler.jobs import setup_scheduler
from bot.health import start_health_server

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def main():
    logger.info("🚀 Starting Apify Deal Bot...")

    # Start health server (required for Render Web Service)
    port = int(os.getenv("PORT", 8000))
    health_runner = await start_health_server(port)

    app = create_client()
    register_handlers(app)

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

        logger.info("🤖 Bot is running. Press Ctrl+C to stop.")
        await stop_event.wait()

        scheduler.shutdown(wait=False)
        await health_runner.cleanup()
        logger.info("👋 Bot stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
