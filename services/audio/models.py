"""Data models for audio service."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Speech-to-Text Models

class STTRequest(BaseModel):
    """Request for speech-to-text transcription."""
    audio_data: Optional[str] = Field(None, description="Base64-encoded audio data")
    audio_path: Optional[str] = Field(None, description="Path to audio file")
    language: Optional[str] = Field(None, description="Language code (e.g., 'en', 'fr') or 'auto'")
    task: str = Field("transcribe", description="Task: 'transcribe' or 'translate'")
    
    # Advanced options
    temperature: float = Field(0.0, description="Sampling temperature")
    vad_filter: bool = Field(True, description="Use voice activity detection")
    word_timestamps: bool = Field(False, description="Include word-level timestamps")


class STTWord(BaseModel):
    """Word-level transcription with timestamp."""
    word: str
    start: float  # seconds
    end: float  # seconds
    probability: float


class STTSegment(BaseModel):
    """Transcription segment with metadata."""
    id: int
    text: str
    start: float  # seconds
    end: float  # seconds
    words: Optional[List[STTWord]] = None


class STTResponse(BaseModel):
    """Response from speech-to-text transcription."""
    text: str = Field(..., description="Transcribed text")
    language: Optional[str] = Field(None, description="Detected language")
    segments: Optional[List[STTSegment]] = Field(None, description="Detailed segments")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")


# Text-to-Speech Models

class TTSRequest(BaseModel):
    """Request for text-to-speech synthesis."""
    text: str = Field(..., description="Text to synthesize")
    voice: Optional[str] = Field(None, description="Voice model to use")
    speed: Optional[float] = Field(None, description="Speech speed multiplier (0.5-2.0)")
    output_format: str = Field("wav", description="Output format: 'wav', 'mp3', 'opus'")
    sample_rate: Optional[int] = Field(None, description="Audio sample rate")


class TTSResponse(BaseModel):
    """Response from text-to-speech synthesis."""
    audio_data: str = Field(..., description="Base64-encoded audio data")
    duration: float = Field(..., description="Audio duration in seconds")
    format: str = Field(..., description="Audio format")
    sample_rate: int = Field(..., description="Sample rate in Hz")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")


# Voice Activity Detection Models

class VADRequest(BaseModel):
    """Request for voice activity detection."""
    audio_data: Optional[str] = Field(None, description="Base64-encoded audio data")
    audio_path: Optional[str] = Field(None, description="Path to audio file")
    threshold: Optional[float] = Field(None, description="Detection threshold (0.0-1.0)")


class VADSegment(BaseModel):
    """Voice activity segment."""
    start: float  # seconds
    end: float  # seconds
    confidence: float


class VADResponse(BaseModel):
    """Response from voice activity detection."""
    has_speech: bool = Field(..., description="Whether speech was detected")
    segments: List[VADSegment] = Field(default_factory=list, description="Speech segments")
    total_speech_duration: float = Field(..., description="Total speech duration in seconds")
    speech_ratio: float = Field(..., description="Ratio of speech to total audio")


# Wake Word Detection Models

class WakeWordRequest(BaseModel):
    """Request for wake word detection."""
    audio_data: str = Field(..., description="Base64-encoded audio data")
    wake_word: Optional[str] = Field(None, description="Wake word to detect")
    threshold: Optional[float] = Field(None, description="Detection threshold")


class WakeWordResponse(BaseModel):
    """Response from wake word detection."""
    detected: bool = Field(..., description="Whether wake word was detected")
    confidence: float = Field(..., description="Detection confidence")
    timestamp: Optional[float] = Field(None, description="Timestamp in audio (seconds)")


# Service Info

class AudioServiceInfo(BaseModel):
    """Audio service information."""
    service: str = "audio_service"
    version: str = "0.1.0"
    status: str = "running"
    capabilities: Dict[str, bool] = Field(
        default_factory=lambda: {
            "stt": True,
            "tts": True,
            "vad": True,
            "wake_word": False
        }
    )
    models: Dict[str, Any] = Field(default_factory=dict)

