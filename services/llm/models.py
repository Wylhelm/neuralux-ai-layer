"""Data models for LLM service."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    """A chat message."""
    role: Role
    content: str


class LLMRequest(BaseModel):
    """Request for LLM completion."""
    messages: List[Message]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop: Optional[List[str]] = None
    stream: bool = False


class LLMResponse(BaseModel):
    """Response from LLM completion."""
    content: str
    model: str
    finish_reason: str = "stop"
    tokens_used: int = 0


class EmbedRequest(BaseModel):
    """Request for text embedding."""
    text: str
    model: Optional[str] = None


class EmbedResponse(BaseModel):
    """Response with embeddings."""
    embedding: List[float]
    model: str


class ModelInfo(BaseModel):
    """Information about a loaded model."""
    name: str
    path: str
    context_size: int
    parameters: Optional[str] = None
    quantization: Optional[str] = None
    loaded: bool = False

