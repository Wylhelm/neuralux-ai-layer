"""Tests for configuration."""

from pathlib import Path
from packages.common.neuralux.config import NeuraluxConfig


def test_config_defaults():
    """Test default configuration values."""
    config = NeuraluxConfig()
    
    assert config.nats_url == "nats://localhost:4222"
    assert config.redis_url == "redis://localhost:6379"
    assert config.profile in ["battery_saver", "balanced", "performance"]
    assert config.telemetry_enabled is False
    assert config.cloud_offload_enabled is False


def test_config_directories():
    """Test that config creates necessary directories."""
    config = NeuraluxConfig()
    
    assert config.data_dir.exists()
    assert config.cache_dir.exists()
    assert config.config_dir.exists()
    
    assert config.data_dir.is_dir()
    assert config.cache_dir.is_dir()
    assert config.config_dir.is_dir()

