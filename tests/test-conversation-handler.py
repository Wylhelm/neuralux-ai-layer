#!/usr/bin/env python3
"""Quick test of conversation handler."""

import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.messaging import MessageBusClient
from neuralux.conversation_handler import ConversationHandler


async def test_conversation():
    """Test the conversation handler directly."""
    print("🧪 Testing Conversation Handler")
    print("=" * 50)
    
    # Connect to message bus
    print("Connecting to message bus...")
    bus = MessageBusClient(NeuraluxConfig())
    try:
        await bus.connect()
        print("✓ Connected to NATS\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False
    
    # Create conversation handler
    print("Creating conversation handler...")
    handler = ConversationHandler(
        message_bus=bus,
        session_id="test_session",
        user_id="test_user",
        approval_callback=lambda action: True  # Auto-approve for testing
    )
    print("✓ Handler created\n")
    
    # Test simple message
    print("Testing message: 'hello, can you help me?'")
    print("Processing...")
    
    try:
        result = await asyncio.wait_for(
            handler.process_message("hello, can you help me?"),
            timeout=15.0
        )
        
        print(f"\n✓ Got result!")
        print(f"  Type: {result.get('type')}")
        print(f"  Message: {result.get('message', '')[:100]}")
        
        if result.get("type") == "response":
            print(f"\n✅ Success! Conversation handler is working.")
            return True
        else:
            print(f"\n⚠️  Unexpected result type: {result.get('type')}")
            return False
            
    except asyncio.TimeoutError:
        print("\n✗ Timeout after 15 seconds")
        print("This means the LLM request is hanging or very slow.")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await bus.disconnect()


if __name__ == "__main__":
    result = asyncio.run(test_conversation())
    sys.exit(0 if result else 1)

