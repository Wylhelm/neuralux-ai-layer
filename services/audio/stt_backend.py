"""Speech-to-Text backend using faster-whisper."""

import base64
import time
from pathlib import Path
from typing import Optional, List
import structlog

logger = structlog.get_logger(__name__)


class STTBackend:
    """Speech-to-Text backend using faster-whisper."""
    
    def __init__(self, config):
        """Initialize STT backend.
        
        Args:
            config: AudioServiceConfig instance
        """
        self.config = config
        self.model = None
        self._model_name = None
        
    def load_model(self) -> None:
        """Load the faster-whisper model."""
        try:
            from faster_whisper import WhisperModel
            
            # Determine device
            device = self.config.stt_device
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
            
            # Determine compute type
            compute_type = self.config.stt_compute_type
            if compute_type == "auto":
                compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(
                "Loading faster-whisper model",
                model=self.config.stt_model,
                device=device,
                compute_type=compute_type
            )
            
            self.model = WhisperModel(
                self.config.stt_model,
                device=device,
                compute_type=compute_type,
                download_root=str(self.config.stt_models_dir)
            )
            self._model_name = self.config.stt_model
            
            logger.info("faster-whisper model loaded successfully")
            
        except ImportError:
            logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error("Failed to load faster-whisper model", error=str(e))
            raise
    
    def transcribe(
        self,
        audio_path: Optional[str] = None,
        audio_data: Optional[str] = None,
        language: Optional[str] = None,
        task: str = "transcribe",
        vad_filter: bool = True,
        word_timestamps: bool = False,
        temperature: float = 0.0
    ) -> dict:
        """Transcribe audio to text.
        
        Args:
            audio_path: Path to audio file
            audio_data: Base64-encoded audio data
            language: Language code or None for auto-detection
            task: "transcribe" or "translate"
            vad_filter: Use voice activity detection
            word_timestamps: Include word-level timestamps
            temperature: Sampling temperature
            
        Returns:
            Dictionary with transcription results
        """
        if self.model is None:
            self.load_model()
        
        start_time = time.time()
        
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
            
            # Get audio duration
            duration = self._get_audio_duration(audio_path)
            
            # Transcribe
            logger.info("Starting transcription", audio_path=audio_path, language=language)
            
            segments, info = self.model.transcribe(
                audio_path,
                language=language if language and language != "auto" else None,
                task=task,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
                temperature=temperature,
                beam_size=5
            )
            
            # Process segments
            segments_list = []
            full_text = []
            
            for segment in segments:
                segment_dict = {
                    "id": segment.id,
                    "text": segment.text,
                    "start": segment.start,
                    "end": segment.end
                }
                
                # Add word timestamps if requested
                if word_timestamps and hasattr(segment, 'words'):
                    segment_dict["words"] = [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        }
                        for word in segment.words
                    ]
                
                segments_list.append(segment_dict)
                full_text.append(segment.text)
            
            processing_time = time.time() - start_time
            
            result = {
                "text": " ".join(full_text).strip(),
                "language": info.language,
                "segments": segments_list if segments_list else None,
                "duration": duration,
                "processing_time": processing_time
            }
            
            logger.info(
                "Transcription completed",
                text_length=len(result["text"]),
                language=result["language"],
                processing_time=processing_time
            )
            
            # Cleanup temp file if created
            if audio_data:
                try:
                    Path(audio_path).unlink()
                except:
                    pass
            
            return result
            
        except Exception as e:
            logger.error("Transcription failed", error=str(e))
            raise
    
    def _get_audio_duration(self, audio_path: str) -> Optional[float]:
        """Get audio file duration in seconds."""
        try:
            import wave
            with wave.open(audio_path, 'r') as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
                return duration
        except:
            # Fallback: try with ffprobe if available
            try:
                import subprocess
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                     '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
                    capture_output=True,
                    text=True
                )
                return float(result.stdout.strip())
            except:
                return None
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
    
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "name": self._model_name or self.config.stt_model,
            "loaded": self.is_loaded(),
            "device": self.config.stt_device
        }

