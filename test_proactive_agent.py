import asyncio
import json
from nats.aio.client import Client as NATS

async def run():
    nc = NATS()
    await nc.connect("nats://localhost:4222")

    event = {
        "event_id": "test-event",
        "event_type": "git_clone",
        "timestamp": "2025-10-31T15:20:00Z",
        "details": {
            "repo_url": "https://github.com/Wylhelm/neuralux-ai-layer.git",
            "clone_dir": "/home/guillaume/test-clone"
        }
    }

    await nc.publish("temporal.event.git_clone", json.dumps(event).encode())
    print("Published git_clone event")

    await nc.close()

if __name__ == '__main__':
    asyncio.run(run())
