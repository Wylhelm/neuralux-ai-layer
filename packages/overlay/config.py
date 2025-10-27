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
    app_name: str = "Neuralux"
    
    # Behavior
    fuzzy_threshold: int = 60  # Minimum match score (0-100)
    max_results: int = 10
    
    # Integration
    nats_url: str = "nats://localhost:4222"
    enable_tray: bool = False  # Show system tray icon with toggle
    tray_icon: str = "auto"  # "auto" uses bundled icon; can be icon name or absolute path
    
    # Voice features
    tts_enabled_default: bool = False  # Auto TTS playback for overlay results
    
    # Voice Activity Detection (VAD) settings
    vad_silence_threshold: float = 0.01  # RMS threshold for silence detection (0.001-0.1)
    vad_silence_duration: float = 1.5    # Seconds of silence before stopping (0.5-5.0)
    vad_max_recording_time: int = 15     # Maximum recording time per turn (5-60 seconds)
    vad_min_recording_time: int = 1      # Minimum recording time before stopping (1-5 seconds)
    
    class Config:
        env_prefix = "OVERLAY_"
        case_sensitive = False

