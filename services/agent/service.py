from __future__ import annotations

import sys
from pathlib import Path
# Add project root to the Python path to allow absolute imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
import signal
from nats.aio.client import Client as NATS
from aiohttp import web

from services.agent import config
from services.agent.patterns import PatternMatcher
from services.agent.notifier import send_notification
from services.agent.suggestion_engine import AISuggestionEngine

# --- Logger Setup ---
logging.basicConfig(level=config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(config.SERVICE_NAME)

class AgentService:
    """The main service for the Proactive Agent."""

    def __init__(self):
        self.nc = NATS()
        self.pattern_matcher: PatternMatcher | None = None
        self.suggestion_engine: AISuggestionEngine | None = None
        self.is_running = False

    async def start(self):
        """Starts the agent service."""
        logger.info("Starting Proactive Agent Service...")
        self.is_running = True

        # Start health check endpoint
        app = web.Application()
        app.router.add_get("/", self.health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8008)
        await site.start()

        try:
            await self.nc.connect(servers=[config.NATS_URL])
            logger.info(f"Connected to NATS at {config.NATS_URL}")

            # Initialise AI suggestion engine once NATS is ready
            self.suggestion_engine = AISuggestionEngine(self.nc)
            self.pattern_matcher = PatternMatcher(self.suggestion_engine)

            await self.nc.subscribe(config.EVENT_STREAM_SUBJECT, cb=self.event_handler)
            logger.info(f"Subscribed to event stream: {config.EVENT_STREAM_SUBJECT}")
        except Exception as e:
            logger.fatal(f"Failed to connect to NATS: {e}")
            return

        logger.info("Proactive Agent Service started successfully.")

    async def stop(self):
        """Stops the agent service gracefully."""
        if not self.is_running:
            return
        logger.info("Stopping Proactive Agent Service...")
        self.is_running = False
        await self.nc.close()
        logger.info("Disconnected from NATS.")
        logger.info("Proactive Agent Service stopped.")

    async def event_handler(self, msg):
        """Handles incoming events from the temporal service."""
        subject = msg.subject
        data = msg.data.decode()
        logger.debug(f"Received event on {subject}")

        if not self.pattern_matcher:
            logger.warning("Pattern matcher not initialised yet; skipping event")
            return

        suggestion = await self.pattern_matcher.match(subject, data)

        if suggestion:
            logger.info(f"Pattern matched! Suggestion: {suggestion['message']}")
            await send_notification(suggestion, self.nc)

    async def health_check(self, request):
        """Health check endpoint."""
        return web.Response(text="OK")

async def main():
    service = AgentService()

    def signal_handler():
        asyncio.create_task(service.stop())

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await service.start()

    while service.is_running:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
