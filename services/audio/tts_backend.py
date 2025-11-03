"""Text-to-Speech backend using Piper."""

import base64
import time
import wave
import io
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class TTSBackend:
    """Text-to-Speech backend using Piper."""
    
    def __init__(self, config):
        """Initialize TTS backend.
        
        Args:
            config: AudioServiceConfig instance
        """
        self.config = config
        self.voice = None
        self._model_name = None
        self._last_used: float = 0.0  # Track last usage time
        self._unload_timeout: int = 300  # Unload after 5 minutes of inactivity
        
    def load_model(self) -> None:
        """Load the Piper voice model."""
        try:
            from piper import PiperVoice
            
            model_path = self.config.tts_models_dir / f"{self.config.tts_model}.onnx"
            config_path = self.config.tts_models_dir / f"{self.config.tts_model}.onnx.json"
            
            logger.info(
                "Loading Piper TTS model",
                model=self.config.tts_model,
                model_path=str(model_path)
            )
            
            # Check if model files exist
            if not model_path.exists():
                logger.warning(
                    "Piper model not found, will need to download",
                    model_path=str(model_path)
                )
                # Create models directory
                self.config.tts_models_dir.mkdir(parents=True, exist_ok=True)
                
                # For now, we'll just note this - in production, we'd auto-download
                logger.info(
                    "To download Piper models, visit: https://github.com/rhasspy/piper/releases"
                )
                raise FileNotFoundError(f"Piper model not found: {model_path}")
            
            self.voice = PiperVoice.load(
                str(model_path),
                config_path=str(config_path) if config_path.exists() else None,
                use_cuda=False  # Piper typically runs on CPU
            )
            self._model_name = self.config.tts_model
            
            logger.info("Piper TTS model loaded successfully")
            
        except ImportError:
            logger.error("piper-tts not installed. Install with: pip install piper-tts")
            # Fallback: use a simple mock for testing
            logger.warning("Using mock TTS backend for testing")
            self._use_mock = True
        except FileNotFoundError as e:
            logger.error("Piper model files not found", error=str(e))
            logger.warning("Using mock TTS backend for testing")
            self._use_mock = True
        except Exception as e:
            logger.error("Failed to load Piper model", error=str(e))
            raise
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        output_format: str = "wav",
        sample_rate: Optional[int] = None
    ) -> dict:
        """Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice: Voice model (if different from default)
            speed: Speech speed multiplier
            output_format: Output format (wav, mp3, opus)
            sample_rate: Output sample rate
            
        Returns:
            Dictionary with audio data and metadata
        """
        if self.voice is None and not hasattr(self, '_use_mock'):
            self.load_model()
        self._last_used = time.time()
        
        start_time = time.time()
        
        try:
            # Use mock if Piper not available
            if hasattr(self, '_use_mock') and self._use_mock:
                return self._mock_synthesize(text, output_format, sample_rate)
            
            logger.info("Synthesizing speech", text_length=len(text))
            
            # Set parameters
            actual_speed = speed if speed is not None else self.config.tts_speed
            actual_sample_rate = sample_rate if sample_rate is not None else self.config.tts_sample_rate
            
            # Synthesize to WAV using Piper
            audio_buffer = io.BytesIO()
            
            # Use Piper's synthesize method which returns a generator of audio chunks
            wav_file = wave.open(audio_buffer, "wb")
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(actual_sample_rate)
            
            # Synthesize with Piper
            for audio_chunk in self.voice.synthesize(text):
                wav_file.writeframes(audio_chunk.audio_int16_bytes)
            
            wav_file.close()
            
            # Get audio data
            audio_buffer.seek(0)
            audio_data = audio_buffer.read()
            
            # Calculate duration
            duration = len(audio_data) / (actual_sample_rate * 2)  # 16-bit = 2 bytes
            
            processing_time = time.time() - start_time
            
            result = {
                "audio_data": base64.b64encode(audio_data).decode('utf-8'),
                "duration": duration,
                "format": output_format,
                "sample_rate": actual_sample_rate,
                "processing_time": processing_time
            }
            
            logger.info(
                "Speech synthesis completed",
                duration=duration,
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            logger.error("Speech synthesis failed", error=str(e))
            # Fallback to mock
            return self._mock_synthesize(text, output_format, sample_rate)
    
    def _mock_synthesize(
        self,
        text: str,
        output_format: str = "wav",
        sample_rate: Optional[int] = None
    ) -> dict:
        """Mock TTS for testing when Piper is not available."""
        logger.info("Using mock TTS synthesis", text_length=len(text))
        
        actual_sample_rate = sample_rate if sample_rate is not None else self.config.tts_sample_rate
        
        # Create a short silent WAV file
        duration = max(1.0, len(text) / 20.0)  # Rough estimate
        num_frames = int(duration * actual_sample_rate)
        
        audio_buffer = io.BytesIO()
        wav_file = wave.open(audio_buffer, "wb")
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(actual_sample_rate)
        wav_file.writeframes(b'\x00\x00' * num_frames)  # Silence
        wav_file.close()
        
        audio_buffer.seek(0)
        audio_data = audio_buffer.read()
        
        return {
            "audio_data": base64.b64encode(audio_data).decode('utf-8'),
            "duration": duration,
            "format": output_format,
            "sample_rate": actual_sample_rate,
            "processing_time": 0.01
        }
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.voice is not None or hasattr(self, '_use_mock')
    
    def should_unload(self) -> bool:
        """Check if model should be unloaded due to inactivity."""
        if self.voice is None or hasattr(self, '_use_mock'):
            return False
        if self._last_used == 0.0:
            return False
        inactive_time = time.time() - self._last_used
        return inactive_time > self._unload_timeout
    
    def unload_model(self) -> None:
        """Unload the current model."""
        if self.voice is not None:
            logger.info("Unloading TTS model", model=self._model_name)
            del self.voice
            self.voice = None
            self._model_name = None
            self._last_used = 0.0
            # Force garbage collection and clear CUDA cache if available
            try:
                import gc
                gc.collect()
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            logger.info("TTS model unloaded")
    
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "name": self._model_name or self.config.tts_model,
            "loaded": self.is_loaded(),
            "mock": hasattr(self, '_use_mock') and self._use_mock
        }

