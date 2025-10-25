#!/usr/bin/env python3
"""
Demo script to test Neuralux without a model.
Tests the infrastructure and message bus functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.messaging import MessageBusClient
from neuralux.logger import setup_logging

async def main():
    print("=" * 60)
    print("  Neuralux AI Layer - Infrastructure Demo")
    print("=" * 60)
    print()
    
    # Setup logging
    setup_logging("demo", "INFO")
    
    # Test configuration
    print("1. Testing Configuration...")
    config = NeuraluxConfig()
    print(f"   ✓ NATS URL: {config.nats_url}")
    print(f"   ✓ Redis URL: {config.redis_url}")
    print(f"   ✓ Profile: {config.profile}")
    print(f"   ✓ Data directory: {config.data_dir}")
    print()
    
    # Test message bus
    print("2. Testing Message Bus...")
    client = MessageBusClient(config)
    
    try:
        await client.connect()
        print("   ✓ Connected to NATS")
        
        # Test pub/sub
        print("   Testing publish/subscribe...")
        received = []
        
        async def handler(msg):
            received.append(msg)
        
        await client.subscribe("demo.test", handler)
        await client.publish("demo.test", {"message": "Hello from Neuralux!"})
        
        # Wait for message
        await asyncio.sleep(0.5)
        
        if received:
            print(f"   ✓ Received: {received[0]}")
        
        # Test request/reply
        print("   Testing request/reply...")
        
        async def echo_handler(request):
            return {"echo": request.get("text", ""), "status": "ok"}
        
        await client.reply_handler("demo.echo", echo_handler)
        
        response = await client.request(
            "demo.echo",
            {"text": "Testing request/reply"},
            timeout=5.0
        )
        
        print(f"   ✓ Response: {response}")
        
        await client.disconnect()
        print("   ✓ Disconnected")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    print()
    print("=" * 60)
    print("  All infrastructure tests passed! ✓")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Download a model:")
    print("   mkdir -p models")
    print("   wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \\")
    print("     -O models/llama-3.2-3b-instruct-q4_k_m.gguf")
    print()
    print("2. Start the LLM service:")
    print("   cd services/llm && python service.py")
    print()
    print("3. Use the AI shell:")
    print("   aish")
    print()

if __name__ == "__main__":
    asyncio.run(main())

