"""Configuration management for Neuralux services."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class NeuraluxConfig(BaseSettings):
    """Base configuration for all Neuralux services."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Message Bus
    nats_url: str = "nats://localhost:4222"
    nats_max_reconnect_attempts: int = 10
    
    # Redis Cache
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # Qdrant Vector Store
    qdrant_url: str = "http://localhost:6333"
    qdrant_grpc_url: str = "localhost:6334"
    qdrant_collection_name: str = "neuralux_vectors"
    
    # Resource Management
    max_vram_gb: int = 8
    profile: str = "balanced"  # battery_saver, balanced, performance
    
    # Privacy & Security
    telemetry_enabled: bool = False
    cloud_offload_enabled: bool = False
    encryption_enabled: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # UI/Settings (user-adjustable)
    ui_llm_model: str = "llama-3.2-3b-instruct-q4_k_m.gguf"
    ui_stt_model: str = "medium"
    
    @property
    def data_dir(self) -> Path:
        """Get the data directory for Neuralux."""
        data_dir = Path.home() / ".local" / "share" / "neuralux"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    @property
    def cache_dir(self) -> Path:
        """Get the cache directory for Neuralux."""
        cache_dir = Path.home() / ".cache" / "neuralux"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    @property
    def config_dir(self) -> Path:
        """Get the config directory for Neuralux."""
        config_dir = Path.home() / ".config" / "neuralux"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def settings_path(self) -> Path:
        return self.config_dir / "settings.json"


def get_config() -> NeuraluxConfig:
    """Get the global configuration instance."""
    return NeuraluxConfig()

