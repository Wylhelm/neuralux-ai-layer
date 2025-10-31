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

from services.temporal import config
from services.temporal.storage import TimelineStorage
from services.temporal.collector import SystemSnapshotCollector, FilesystemCollector, CommandCollector
from services.temporal.models import BaseEvent, CommandEvent

# --- Logger Setup ---
logging.basicConfig(level=config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(config.SERVICE_NAME)

class TemporalService:
    """The main service class for temporal intelligence."""

    def __init__(self):
        self.storage = TimelineStorage()
        self.snapshot_collector = SystemSnapshotCollector(self.handle_event)
        self.fs_collector = FilesystemCollector(self.handle_event)
        self.command_collector = CommandCollector(self._handle_command_event)
        self.nc = NATS()
        self.is_running = False

    async def start(self):
        """Starts all components of the service."""
        logger.info("Starting Temporal Service...")
        self.is_running = True
        
        # Start health check endpoint
        app = web.Application()
        app.router.add_get("/", self.health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8007)
        await site.start()
        
        # Connect to NATS
        try:
            await self.nc.connect(servers=[config.NATS_URL])
            logger.info(f"Connected to NATS at {config.NATS_URL}")
            await self.command_collector.start(self.nc)
        except Exception as e:
            logger.fatal(f"Failed to connect to NATS: {e}")
            return

        # Start collectors
        await self.snapshot_collector.start()
        self.fs_collector.start()
        
        logger.info("Temporal Service started successfully.")

    async def stop(self):
        """Stops all components of the service gracefully."""
        if not self.is_running:
            return
        logger.info("Stopping Temporal Service...")
        self.is_running = False

        # Stop collectors
        await self.snapshot_collector.stop()
        self.fs_collector.stop()
        await self.command_collector.stop()

        # Disconnect from NATS
        await self.nc.close()
        logger.info("Disconnected from NATS.")

        # Close storage
        self.storage.close()
        
        logger.info("Temporal Service stopped.")

    async def handle_event(self, event: BaseEvent):
        """Callback to add events to storage and publish them to NATS."""
        # First, store the event in the database
        self.storage.add_event(event)

        # Then, publish the event for other services to consume
        try:
            subject = f"temporal.event.{event.event_type}"
            payload = event.model_dump_json().encode()
            await self.nc.publish(subject, payload)
            logger.debug(f"Published event {event.event_id} to {subject}")
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")

    async def _handle_command_event(self, event: CommandEvent):
        """Handles incoming command events from the command collector."""
        try:
            await self.handle_event(event)
            logger.info(f"Received and stored command event: {event.command}")
        except Exception as e:
            logger.error(f"Error processing command event: {e}")

    async def health_check(self, request):
        """Health check endpoint."""
        return web.Response(text="OK")

async def main():
    service = TemporalService()
    
    def signal_handler():
        asyncio.create_task(service.stop())

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await service.start()
    
    # Keep the service running until a stop is requested
    while service.is_running:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
