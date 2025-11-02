import asyncio
import uuid
from pathlib import Path
import sys

# Add common package to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "common"))

from neuralux.messaging import MessageBusClient
from neuralux.config import NeuraluxConfig

async def main():
    """Connects to the message bus and requests a song generation."""
    config = NeuraluxConfig()
    message_bus = MessageBusClient(config)
    await message_bus.connect()

    conversation_id = str(uuid.uuid4())
    payload = {
        "prompt": "a happy, pop rock song about a robot learning to code",
        "user_id": "test_user",
        "conversation_id": conversation_id,
    }

    print(f"Sending music generation request with conversation_id: {conversation_id}")
    print(f"Prompt: {payload['prompt']}")

    response_received = asyncio.Event()
    response_data = {}

    async def response_callback(msg):
        """Callback to handle the response from the service."""
        nonlocal response_data
        print("Received response:")
        print(msg)
        response_data = msg
        response_received.set()

    await message_bus.subscribe(f"conversation.{conversation_id}", response_callback)
    await message_bus.publish("agent.music.generate", payload)

    try:
        await asyncio.wait_for(response_received.wait(), timeout=300.0)  # 5-minute timeout
        if response_data.get("type") == "music_result":
            print(f"\\n✅ Success! Song generated and saved to: {response_data.get('file_path')}")
        else:
            print(f"\\n❌ Failed. Error: {response_data.get('content', 'Unknown error')}")
    except asyncio.TimeoutError:
        print("\\n❌ Timed out waiting for a response from the music service.")
    finally:
        await message_bus.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
