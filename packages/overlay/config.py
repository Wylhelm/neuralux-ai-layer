"""Configuration for GUI overlay."""

from pathlib import Path
from pydantic_settings import BaseSettings


class OverlayConfig(BaseSettings):
    """Configuration for the overlay."""
    
    # Window settings
    window_width: int = 800
    window_height: int = 600
    window_opacity: float = 0.95
    fullscreen: bool = False  # If true, maximize window and center content
    
    # Hotkey
    hotkey: str = "<Control>space"  # GTK/X11 accelerator format (default avoids Alt+Space conflict)
    
    # Appearance
    theme: str = "dark"  # dark or light
    font_size: int = 14
    
    # Behavior
    fuzzy_threshold: int = 60  # Minimum match score (0-100)
    max_results: int = 10
    
    # Integration
    nats_url: str = "nats://localhost:4222"
    
    class Config:
        env_prefix = "OVERLAY_"
        case_sensitive = False

