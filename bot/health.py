import logging
from aiohttp import web

logger = logging.getLogger(__name__)


async def start_health_server(port: int = 8000):
    app = web.Application()
    app.router.add_get("/", lambda r: web.json_response({"status": "ok"}))
    app.router.add_get("/health", lambda r: web.json_response({"status": "ok"}))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"✅ Health server on port {port}")
    return runner
