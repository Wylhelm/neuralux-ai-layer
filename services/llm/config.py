"""Configuration for LLM service."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMServiceConfig(BaseSettings):
    """Configuration for the LLM service."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Service
    service_name: str = "llm_service"
    service_port: int = 8000
    host: str = "0.0.0.0"
    
    # Model paths
    model_path: Path = Path(__file__).parent.parent.parent / "models"
    default_model: str = "llama-3.2-3b-instruct-q4_k_m.gguf"
    
    # Model parameters
    max_context: int = 8192
    gpu_layers: int = -1  # -1 for auto, 0 for CPU only
    threads: int = 8
    batch_size: int = 512
    
    # Generation defaults
    default_temperature: float = 0.7
    default_max_tokens: int = 1024
    default_top_p: float = 0.9
    default_top_k: int = 40
    
    # Message bus subjects
    llm_request_subject: str = "ai.llm.request"
    llm_stream_subject: str = "ai.llm.stream"
    llm_embed_subject: str = "ai.llm.embed"
    
    @property
    def model_full_path(self) -> Path:
        """Get full path to the default model."""
        return self.model_path / self.default_model

