#!/usr/bin/env python3
import asyncio
import json
from nats.aio.client import Client as NATS

NATS_URL = "nats://localhost:4222"
ACTION_PREFIX = "system.action"

async def test_system_service():
    """Sends a few test requests to the system service."""
    
    nc = NATS()
    try:
        await nc.connect(servers=[NATS_URL])
        
        # --- Test 1: List all processes ---
        print("🚀 Requesting to list all processes...")
        try:
            response = await nc.request(f"{ACTION_PREFIX}.process.list", b'', timeout=2)
            data = json.loads(response.data.decode())
            if data.get("status") == "success":
                print(f"✅ Success! Found {len(data.get('data', []))} processes.")
            else:
                print(f"❌ Failed: {data.get('message')}")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

        # --- Test 2: Kill a non-existent process ---
        print("\n🚀 Requesting to kill a non-existent process (PID 99999)...")
        try:
            payload = json.dumps({"pid": 99999}).encode()
            response = await nc.request(f"{ACTION_PREFIX}.process.kill", payload, timeout=2)
            data = json.loads(response.data.decode())
            if data.get("status") == "error" and "No process" in data.get("message", ""):
                print("✅ Success! Service correctly reported that the process does not exist.")
            else:
                print(f"❌ Failed: {data}")
        except Exception as e:
            print(f"❌ An error occurred: {e}")

        await nc.close()
        
    except Exception as e:
        print(f"❌ Failed to connect or communicate with NATS: {e}")
        print("   Is NATS and the system_service running? (make start-all)")

if __name__ == "__main__":
    asyncio.run(test_system_service())
