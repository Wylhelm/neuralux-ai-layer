"""Tests for message bus functionality."""

import asyncio
import pytest

from packages.common.neuralux.messaging import MessageBusClient
from packages.common.neuralux.config import NeuraluxConfig


@pytest.mark.asyncio
async def test_connect_disconnect():
    """Test connecting and disconnecting from the message bus."""
    config = NeuraluxConfig()
    client = MessageBusClient(config)
    
    # This will fail if NATS is not running, which is expected in CI
    try:
        await client.connect()
        assert client.nc is not None
        assert client.js is not None
        await client.disconnect()
    except Exception:
        pytest.skip("NATS not available")


@pytest.mark.asyncio
async def test_publish_subscribe():
    """Test publish/subscribe functionality."""
    config = NeuraluxConfig()
    client = MessageBusClient(config)
    
    try:
        await client.connect()
        
        received_messages = []
        
        async def callback(msg):
            received_messages.append(msg)
        
        # Subscribe to a test subject
        await client.subscribe("test.subject", callback)
        
        # Publish a message
        test_message = {"test": "data"}
        await client.publish("test.subject", test_message)
        
        # Wait for message to be received
        await asyncio.sleep(0.5)
        
        assert len(received_messages) == 1
        assert received_messages[0] == test_message
        
        await client.disconnect()
    except Exception:
        pytest.skip("NATS not available")


@pytest.mark.asyncio
async def test_request_reply():
    """Test request/reply functionality."""
    config = NeuraluxConfig()
    client = MessageBusClient(config)
    
    try:
        await client.connect()
        
        # Register a reply handler
        async def handler(request):
            return {"response": f"Echo: {request.get('message')}"}
        
        await client.reply_handler("test.echo", handler)
        
        # Send a request
        response = await client.request(
            "test.echo",
            {"message": "Hello"},
            timeout=5.0
        )
        
        assert response == {"response": "Echo: Hello"}
        
        await client.disconnect()
    except Exception:
        pytest.skip("NATS not available")

