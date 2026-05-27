"""
Tiny HTTP server that runs alongside the Telegram bot.
Required for Render Web Service (free tier) — Render needs a port to stay alive.
UptimeRobot pings /health every 5 mins to prevent sleep.
"""
import asyncio
import logging
from aiohttp import web

logger = logging.getLogger(__name__)


async def health(request):
    return web.json_response({"status": "ok", "bot": "running"})


async def start_health_server(port: int = 8000):
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"✅ Health server running on port {port}")
    return runner
