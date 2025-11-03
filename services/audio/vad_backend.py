"""Voice Activity Detection backend using Silero VAD."""

import base64
import time
import torch
import torchaudio
from pathlib import Path
from typing import Optional, List
import structlog

logger = structlog.get_logger(__name__)


class VADBackend:
    """Voice Activity Detection backend using Silero VAD."""
    
    def __init__(self, config):
        """Initialize VAD backend.
        
        Args:
            config: AudioServiceConfig instance
        """
        self.config = config
        self.model = None
        self.utils = None
        self._last_used: float = 0.0  # Track last usage time
        self._unload_timeout: int = 300  # Unload after 5 minutes of inactivity
        
    def load_model(self) -> None:
        """Load the Silero VAD model."""
        try:
            logger.info("Loading Silero VAD model")
            
            # Load Silero VAD from torch hub
            self.model, self.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False  # Use PyTorch version
            )
            
            logger.info("Silero VAD model loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load Silero VAD model", error=str(e))
            logger.warning("VAD will be disabled")
            raise
    
    def detect(
        self,
        audio_path: Optional[str] = None,
        audio_data: Optional[str] = None,
        threshold: Optional[float] = None
    ) -> dict:
        """Detect voice activity in audio.
        
        Args:
            audio_path: Path to audio file
            audio_data: Base64-encoded audio data
            threshold: Detection threshold (0.0-1.0)
            
        Returns:
            Dictionary with detection results
        """
        if self.model is None:
            self.load_model()
        self._last_used = time.time()
        
        try:
            # Handle audio input
            if audio_data:
                # Decode base64 audio and save to temp file
                import tempfile
                audio_bytes = base64.b64decode(audio_data)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_bytes)
                    temp_path = f.name
                audio_path = temp_path
            
            if not audio_path or not Path(audio_path).exists():
                raise ValueError("No valid audio input provided")
            
            # Load audio
            wav, sample_rate = torchaudio.load(audio_path)
            
            # Resample to 16kHz if needed (Silero VAD expects 16kHz)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                wav = resampler(wav)
                sample_rate = 16000
            
            # Convert to mono if stereo
            if wav.shape[0] > 1:
                wav = torch.mean(wav, dim=0, keepdim=True)
            
            # Get speech timestamps
            actual_threshold = threshold if threshold is not None else self.config.vad_threshold
            
            get_speech_timestamps = self.utils[0]
            speech_timestamps = get_speech_timestamps(
                wav,
                self.model,
                threshold=actual_threshold,
                sampling_rate=sample_rate,
                min_silence_duration_ms=self.config.vad_min_silence_duration,
                speech_pad_ms=self.config.vad_speech_pad
            )
            
            # Calculate metrics
            segments = []
            total_speech_duration = 0.0
            
            for ts in speech_timestamps:
                start = ts['start'] / sample_rate
                end = ts['end'] / sample_rate
                duration = end - start
                total_speech_duration += duration
                
                segments.append({
                    "start": start,
                    "end": end,
                    "confidence": 1.0  # Silero doesn't provide per-segment confidence
                })
            
            total_duration = wav.shape[1] / sample_rate
            speech_ratio = total_speech_duration / total_duration if total_duration > 0 else 0.0
            
            result = {
                "has_speech": len(segments) > 0,
                "segments": segments,
                "total_speech_duration": total_speech_duration,
                "speech_ratio": speech_ratio
            }
            
            logger.info(
                "VAD detection completed",
                has_speech=result["has_speech"],
                segments=len(segments),
                speech_ratio=speech_ratio
            )
            
            # Cleanup temp file if created
            if audio_data:
                try:
                    Path(audio_path).unlink()
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error("VAD detection failed", error=str(e))
            raise
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
    
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
            logger.info("Unloading VAD model")
            del self.model
            self.model = None
            self.utils = None
            self._last_used = 0.0
            # Force garbage collection and clear CUDA cache if available
            try:
                import gc
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            logger.info("VAD model unloaded")
    
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "name": "silero-vad",
            "loaded": self.is_loaded()
        }

