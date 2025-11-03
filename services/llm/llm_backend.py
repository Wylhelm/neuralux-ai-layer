"""LLM backend using llama.cpp."""

import os
import time
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

import structlog
from llama_cpp import Llama, LlamaGrammar

from config import LLMServiceConfig
from models import LLMRequest, LLMResponse, Message, Role

logger = structlog.get_logger(__name__)


class LlamaCppBackend:
    """Backend for running LLMs using llama.cpp."""
    
    def __init__(self, config: LLMServiceConfig):
        """Initialize the llama.cpp backend."""
        self.config = config
        self.model: Optional[Llama] = None
        self.current_model_name: Optional[str] = None
        self._last_used: float = 0.0  # Track last usage time
        self._unload_timeout: int = 300  # Unload after 5 minutes of inactivity (configurable)
        
    def load_model(self, model_path: Optional[Path] = None) -> None:
        """Load a model from disk."""
        if model_path is None:
            model_path = self.config.model_full_path
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                f"Please download a model and place it in {self.config.model_path}\n"
                f"Recommended: Llama-3.2-3B-Instruct Q4_K_M GGUF format"
            )
        
        logger.info(
            "Loading model",
            model_path=str(model_path),
            gpu_layers=self.config.gpu_layers,
            context_size=self.config.max_context,
        )
        
        try:
            self.model = Llama(
                model_path=str(model_path),
                n_ctx=self.config.max_context,
                n_gpu_layers=self.config.gpu_layers,
                n_threads=self.config.threads,
                n_batch=self.config.batch_size,
                verbose=False,
            )
            self.current_model_name = model_path.stem
            logger.info("Model loaded successfully", model=self.current_model_name)
        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            raise
    
    def _format_messages(self, messages: List[Message]) -> str:
        """Format messages into a prompt string."""
        # Simple chat format - can be improved with model-specific templates
        prompt_parts = []
        
        for msg in messages:
            if msg.role == Role.SYSTEM:
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == Role.USER:
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == Role.ASSISTANT:
                prompt_parts.append(f"Assistant: {msg.content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion for the given request."""
        self.ensure_model_loaded()
        
        prompt = self._format_messages(request.messages)
        
        temperature = request.temperature or self.config.default_temperature
        max_tokens = request.max_tokens or self.config.default_max_tokens
        top_p = request.top_p or self.config.default_top_p
        top_k = request.top_k or self.config.default_top_k
        
        logger.debug(
            "Generating completion",
            prompt_length=len(prompt),
            max_tokens=max_tokens,
        )
        
        try:
            response = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=request.stop or ["User:", "\n\nUser:"],
                echo=False,
            )
            
            content = response["choices"][0]["text"].strip()
            tokens_used = response["usage"]["total_tokens"]
            
            return LLMResponse(
                content=content,
                model=self.current_model_name or "unknown",
                tokens_used=tokens_used,
            )
        except Exception as e:
            logger.error("Generation failed", error=str(e))
            raise
    
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Generate a streaming completion."""
        self.ensure_model_loaded()
        
        prompt = self._format_messages(request.messages)
        
        temperature = request.temperature or self.config.default_temperature
        max_tokens = request.max_tokens or self.config.default_max_tokens
        top_p = request.top_p or self.config.default_top_p
        top_k = request.top_k or self.config.default_top_k
        
        try:
            stream = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=request.stop or ["User:", "\n\nUser:"],
                echo=False,
                stream=True,
            )
            
            for chunk in stream:
                text = chunk["choices"][0]["text"]
                if text:
                    yield text
        except Exception as e:
            logger.error("Streaming generation failed", error=str(e))
            raise
    
    def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings for text."""
        self.ensure_model_loaded()
        
        try:
            embedding = self.model.embed(text)
            return embedding
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise
    
    def ensure_model_loaded(self) -> None:
        """Ensure model is loaded (lazy loading)."""
        if self.model is None:
            self.load_model()
        self._last_used = time.time()
    
    def should_unload(self) -> bool:
        """Check if model should be unloaded due to inactivity."""
        if self.model is None:
            return False
        if self._last_used == 0.0:
            return False
        inactive_time = time.time() - self._last_used
        return inactive_time > self._unload_timeout
    
    def unload_model(self) -> None:
        """Unload the current model."""
        if self.model:
            logger.info("Unloading LLM model", model=self.current_model_name)
            del self.model
            self.model = None
            self.current_model_name = None
            self._last_used = 0.0
            # Force garbage collection and clear CUDA cache if available
            try:
                import gc
                gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            logger.info("Model unloaded")

