"""Main LLM service implementation."""

import asyncio
import sys
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.logger import setup_logging
from neuralux.messaging import MessageBusClient

from config import LLMServiceConfig
from llm_backend import LlamaCppBackend
from models import (
    EmbedRequest,
    EmbedResponse,
    LLMRequest,
    LLMResponse,
    ModelInfo,
)

logger = structlog.get_logger(__name__)


class LLMService:
    """LLM Service that provides language model capabilities."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.config = LLMServiceConfig()
        self.neuralux_config = NeuraluxConfig()
        self.message_bus = MessageBusClient(self.neuralux_config)
        self.backend = LlamaCppBackend(self.config)
        self.app = FastAPI(title="Neuralux LLM Service")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def root():
            return {"service": "neuralux-llm", "version": "0.1.0", "status": "running"}
        
        @self.app.post("/v1/chat/completions", response_model=LLMResponse)
        async def chat_completions(request: LLMRequest):
            """Handle chat completion requests."""
            try:
                if request.stream:
                    return StreamingResponse(
                        self._stream_response(request),
                        media_type="text/event-stream"
                    )
                else:
                    return await self.backend.generate(request)
            except Exception as e:
                logger.error("Chat completion failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/v1/embeddings", response_model=EmbedResponse)
        async def embeddings(request: EmbedRequest):
            """Handle embedding requests."""
            try:
                embedding = self.backend.get_embeddings(request.text)
                return EmbedResponse(
                    embedding=embedding,
                    model=self.backend.current_model_name or "unknown"
                )
            except Exception as e:
                logger.error("Embedding generation failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/v1/models", response_model=ModelInfo)
        async def get_model_info():
            """Get information about the current model."""
            return ModelInfo(
                name=self.backend.current_model_name or "none",
                path=str(self.config.model_full_path),
                context_size=self.config.max_context,
                loaded=self.backend.model is not None,
            )
        
        @self.app.post("/v1/model/load")
        async def load_model(model_name: str):
            """Load/swap model by filename (in configured model_path)."""
            try:
                # Publish start event
                try:
                    await self.message_bus.publish("ai.llm.reload.events", {"event": "start", "model": model_name})
                except Exception:
                    pass
                # Update config default and load
                self.config.default_model = model_name
                self.backend.unload_model()
                self.backend.load_model()
                try:
                    await self.message_bus.publish("ai.llm.reload.events", {"event": "done", "model": model_name})
                except Exception:
                    pass
                return {"status": "ok", "model": model_name}
            except Exception as e:
                try:
                    await self.message_bus.publish("ai.llm.reload.events", {"event": "error", "model": model_name, "error": str(e)})
                except Exception:
                    pass
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _stream_response(self, request: LLMRequest):
        """Stream response generator."""
        async for chunk in self.backend.generate_stream(request):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    async def _handle_llm_request(self, request_data: dict) -> dict:
        """Handle LLM request from message bus."""
        try:
            request = LLMRequest(**request_data)
            response = await self.backend.generate(request)
            return response.model_dump()
        except Exception as e:
            logger.error("Message bus request failed", error=str(e))
            return {"error": str(e)}
    
    async def _handle_embed_request(self, request_data: dict) -> dict:
        """Handle embedding request from message bus."""
        try:
            request = EmbedRequest(**request_data)
            embedding = self.backend.get_embeddings(request.text)
            response = EmbedResponse(
                embedding=embedding,
                model=self.backend.current_model_name or "unknown"
            )
            return response.model_dump()
        except Exception as e:
            logger.error("Embedding request failed", error=str(e))
            return {"error": str(e)}
    
    async def start(self):
        """Start the LLM service."""
        setup_logging(self.config.service_name, self.neuralux_config.log_level)
        logger.info("Starting LLM service (models will load on first use)")
        
        # Don't load model on startup - use lazy loading instead
        
        # Start background task for automatic model unloading
        import asyncio
        asyncio.create_task(self._unload_inactive_models())
        
        # Connect to message bus
        try:
            await self.message_bus.connect()
            
            # Register message handlers
            await self.message_bus.reply_handler(
                self.config.llm_request_subject,
                self._handle_llm_request
            )
            await self.message_bus.reply_handler(
                self.config.llm_embed_subject,
                self._handle_embed_request
            )
            
            logger.info("Message bus handlers registered")
        except Exception as e:
            logger.error("Failed to connect to message bus", error=str(e))
            logger.warning("Service will run in REST-only mode")
    
    async def stop(self):
        """Stop the LLM service."""
        logger.info("Stopping LLM service")
        await self.message_bus.disconnect()
        self.backend.unload_model()
    
    async def _unload_inactive_models(self):
        """Background task to unload inactive models."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                if self.backend.should_unload():
                    logger.info("Unloading inactive LLM model")
                    self.backend.unload_model()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in model unload task", error=str(e))


# Create service instance
service = LLMService()


if __name__ == "__main__":
    import uvicorn
    
    async def startup():
        await service.start()
    
    async def shutdown():
        await service.stop()
    
    # Add startup/shutdown handlers
    service.app.add_event_handler("startup", startup)
    service.app.add_event_handler("shutdown", shutdown)
    
    # Run the service
    uvicorn.run(
        service.app,
        host=service.config.host,
        port=service.config.service_port,
        log_level=service.neuralux_config.log_level.lower(),
    )

