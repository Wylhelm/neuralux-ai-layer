from dataclasses import dataclass
import os
from pathlib import Path

@dataclass
class MusicServiceConfig:
    """Configuration for the Music Generation Service."""
    model_name: str = os.getenv("MUSIC_MODEL_NAME", "facebook/musicgen-medium")
    # Construct path relative to the project root (2 levels up from this file)
    model_cache_dir: str = os.getenv("MUSIC_MODEL_CACHE_DIR", str(Path(__file__).resolve().parents[2] / "models" / "music"))
    output_dir: str = os.getenv("MUSIC_OUTPUT_DIR", str(Path.home() / "Music"))
    service_port: int = int(os.getenv("MUSIC_SERVICE_PORT", 8010))
