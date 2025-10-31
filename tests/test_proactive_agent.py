#!/usr/bin/env python3
import asyncio
import json
from nats.aio.client import Client as NATS

NATS_URL = "nats://localhost:4222"
COMMAND_SUBJECT = "temporal.command.new"

async def test_agent():
    """Publishes a fake 'git clone' command event to NATS to test the agent."""
    
    print("🚀 Publishing a fake 'git clone' event to test the proactive agent...")

    # This mimics the event that a shell hook would send
    fake_event = {
        "event_type": "command",
        "command": "git clone https://github.com/some/repo.git",
        "cwd": "/home/guillaume/Projects",
        "exit_code": 0,
        "user": "guillaume"
    }
    
    nc = NATS()
    try:
        await nc.connect(servers=[NATS_URL])
        
        # The temporal service listens on `temporal.command.new`, processes it,
        # and then re-publishes it for the agent.
        await nc.publish(COMMAND_SUBJECT, json.dumps(fake_event).encode())
        
        print("✅ Event published successfully.")
        print("👀 Check your desktop notifications for a suggestion from the Neuralux Agent.")
        
        await nc.close()
        
    except Exception as e:
        print(f"❌ Failed to publish event: {e}")
        print("   Is NATS running? (make start)")

if __name__ == "__main__":
    asyncio.run(test_agent())
