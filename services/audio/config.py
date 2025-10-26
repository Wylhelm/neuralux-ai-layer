"""Configuration for audio service."""

from pathlib import Path
from pydantic_settings import BaseSettings


class AudioServiceConfig(BaseSettings):
    """Configuration for audio service."""
    
    # Service
    service_name: str = "audio_service"
    service_port: int = 8006
    host: str = "0.0.0.0"
    
    # NATS subjects
    nats_subject_prefix: str = "ai.audio"
    
    # Speech-to-Text (STT)
    stt_model: str = "base"  # tiny, base, small, medium, large
    stt_language: str = "en"  # Language code (en, fr, es, etc.) or "auto"
    stt_device: str = "auto"  # "cuda", "cpu", or "auto"
    stt_compute_type: str = "auto"  # "int8", "float16", "float32", or "auto"
    
    # Text-to-Speech (TTS)
    tts_model: str = "en_US-lessac-medium"  # Piper voice model
    tts_speed: float = 1.0  # Speech speed multiplier
    tts_sample_rate: int = 22050  # Audio sample rate
    
    # Voice Activity Detection (VAD)
    vad_enabled: bool = True
    vad_threshold: float = 0.5  # Threshold for speech detection (0.0-1.0)
    vad_min_silence_duration: int = 300  # Minimum silence in ms to consider end of speech
    vad_speech_pad: int = 30  # Padding around speech segments in ms
    
    # Audio settings
    audio_sample_rate: int = 16000  # Recording sample rate
    audio_channels: int = 1  # Mono audio
    audio_chunk_duration: float = 0.5  # Chunk duration in seconds for streaming
    
    # Model paths
    models_dir: Path = Path(__file__).parent.parent.parent / "models" / "audio"
    stt_models_dir: Path = models_dir / "whisper"
    tts_models_dir: Path = models_dir / "piper"
    vad_models_dir: Path = models_dir / "silero-vad"
    
    # Cache
    cache_dir: Path = Path.home() / ".cache" / "neuralux" / "audio"
    
    # Wake word detection
    wake_word_enabled: bool = False
    wake_word: str = "neuralux"
    wake_word_threshold: float = 0.5
    
    class Config:
        env_prefix = "AUDIO_"
        case_sensitive = False

