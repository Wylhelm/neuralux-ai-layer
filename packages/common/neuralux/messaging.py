"""Message bus client wrapper for NATS."""

import asyncio
import json
from typing import Any, Callable, Dict, Optional, Union

import nats
from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext
import structlog

from .config import NeuraluxConfig

logger = structlog.get_logger(__name__)


class MessageBusClient:
    """Wrapper for NATS message bus with JetStream support."""
    
    def __init__(self, config: Optional[NeuraluxConfig] = None):
        """Initialize the message bus client."""
        self.config = config or NeuraluxConfig()
        self.nc: Optional[NATSClient] = None
        self.js: Optional[JetStreamContext] = None
        self._subscriptions: Dict[str, Any] = {}
        
    async def connect(self) -> None:
        """Connect to NATS server."""
        try:
            self.nc = await nats.connect(
                servers=[self.config.nats_url],
                max_reconnect_attempts=self.config.nats_max_reconnect_attempts,
                reconnect_time_wait=2,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback,
            )
            self.js = self.nc.jetstream()
            logger.info("Connected to NATS", url=self.config.nats_url)
        except Exception as e:
            logger.error("Failed to connect to NATS", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            logger.info("Disconnected from NATS")
    
    async def publish(
        self,
        subject: str,
        message: Union[Dict[str, Any], str, bytes],
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Publish a message to a subject."""
        if not self.nc:
            raise RuntimeError("Not connected to NATS")
        
        # Convert message to bytes
        if isinstance(message, dict):
            payload = json.dumps(message).encode()
        elif isinstance(message, str):
            payload = message.encode()
        else:
            payload = message
        
        await self.nc.publish(subject, payload, headers=headers)
        logger.debug("Published message", subject=subject, size=len(payload))
    
    async def request(
        self,
        subject: str,
        message: Union[Dict[str, Any], str, bytes],
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """Send a request and wait for a reply."""
        if not self.nc:
            raise RuntimeError("Not connected to NATS")
        
        # Convert message to bytes
        if isinstance(message, dict):
            payload = json.dumps(message).encode()
        elif isinstance(message, str):
            payload = message.encode()
        else:
            payload = message
        
        try:
            response = await self.nc.request(subject, payload, timeout=timeout)
            return json.loads(response.data.decode())
        except asyncio.TimeoutError:
            logger.error("Request timeout", subject=subject, timeout=timeout)
            raise
        except Exception as e:
            logger.error("Request failed", subject=subject, error=str(e))
            raise
    
    async def subscribe(
        self,
        subject: str,
        callback: Callable[[Dict[str, Any]], None],
        queue: Optional[str] = None,
    ) -> None:
        """Subscribe to a subject."""
        if not self.nc:
            raise RuntimeError("Not connected to NATS")
        
        async def message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                await callback(data)
            except Exception as e:
                logger.error(
                    "Error handling message",
                    subject=subject,
                    error=str(e)
                )
        
        sub = await self.nc.subscribe(subject, queue=queue, cb=message_handler)
        self._subscriptions[subject] = sub
        logger.info("Subscribed to subject", subject=subject, queue=queue)
    
    async def reply_handler(
        self,
        subject: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """Register a request/reply handler."""
        if not self.nc:
            raise RuntimeError("Not connected to NATS")
        
        async def reply_callback(msg):
            try:
                request_data = json.loads(msg.data.decode())
                response_data = await handler(request_data)
                response_payload = json.dumps(response_data).encode()
                await msg.respond(response_payload)
            except Exception as e:
                logger.error(
                    "Error handling request",
                    subject=subject,
                    error=str(e)
                )
                error_response = {"error": str(e)}
                await msg.respond(json.dumps(error_response).encode())
        
        sub = await self.nc.subscribe(subject, cb=reply_callback)
        self._subscriptions[subject] = sub
        logger.info("Registered reply handler", subject=subject)
    
    async def _error_callback(self, e: Exception) -> None:
        """Handle NATS errors."""
        logger.error("NATS error", error=str(e))
    
    async def _disconnected_callback(self) -> None:
        """Handle NATS disconnection."""
        logger.warning("Disconnected from NATS")
    
    async def _reconnected_callback(self) -> None:
        """Handle NATS reconnection."""
        logger.info("Reconnected to NATS")


# Convenience function for getting a client instance
_client_instance: Optional[MessageBusClient] = None


async def get_message_bus() -> MessageBusClient:
    """Get or create the global message bus client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = MessageBusClient()
        await _client_instance.connect()
    return _client_instance

