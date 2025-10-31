import sys
from pathlib import Path
# Add project root to the Python path to allow absolute imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import logging
import signal
import json
from nats.aio.client import Client as NATS
from aiohttp import web

from services.system import config
from services.system.actions import ACTION_MAP

# --- Logger Setup ---
logging.basicConfig(level=config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(config.SERVICE_NAME)

class SystemService:
    """Exposes system control actions via NATS."""

    def __init__(self):
        self.nc = NATS()
        self.is_running = False

    async def start(self):
        """Starts the system service."""
        logger.info("Starting System Service...")
        self.is_running = True

        # Start health check endpoint
        app = web.Application()
        app.router.add_get("/", self.health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8009)
        await site.start()

        try:
            await self.nc.connect(servers=[config.NATS_URL])
            logger.info(f"Connected to NATS at {config.NATS_URL}")
            
            subject = f"{config.ACTION_SUBJECT_PREFIX}.>"
            await self.nc.subscribe(subject, cb=self.action_handler)
            logger.info(f"Subscribed to action stream: {subject}")
            
        except Exception as e:
            logger.fatal(f"Failed to connect to NATS: {e}")
            return

        logger.info("System Service started successfully.")

    async def stop(self):
        """Stops the system service gracefully."""
        if not self.is_running:
            return
        logger.info("Stopping System Service...")
        self.is_running = False
        await self.nc.close()
        logger.info("Disconnected from NATS.")
        logger.info("System Service stopped.")

    async def action_handler(self, msg):
        """Handles incoming action requests."""
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        
        action_name = subject.replace(f"{config.ACTION_SUBJECT_PREFIX}.", "")
        logger.info(f"Received request for action '{action_name}'")

        if action_name in ACTION_MAP:
            try:
                params = json.loads(data) if data else {}
                result = ACTION_MAP[action_name](params)
            except json.JSONDecodeError:
                result = json.dumps({"status": "error", "message": "Invalid JSON payload."})
            except Exception as e:
                result = json.dumps({"status": "error", "message": f"An unexpected error occurred: {e}"})
        else:
            result = json.dumps({"status": "error", "message": f"Unknown action: {action_name}"})

        if reply:
            await self.nc.publish(reply, result.encode())
            logger.debug(f"Sent reply for action '{action_name}'")

    async def health_check(self, request):
        """Health check endpoint."""
        return web.Response(text="OK")

async def main():
    service = SystemService()

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
