"""Audio service main entry point."""

import asyncio
import sys
from pathlib import Path
import structlog
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import Response

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.logger import setup_logging
from neuralux.messaging import MessageBusClient

from config import AudioServiceConfig
from models import (
    STTRequest,
    STTResponse,
    TTSRequest,
    TTSResponse,
    VADRequest,
    VADResponse,
    AudioServiceInfo
)
from stt_backend import STTBackend
from tts_backend import TTSBackend
from vad_backend import VADBackend

logger = structlog.get_logger(__name__)


class AudioService:
    """Audio service for speech-to-text, text-to-speech, and voice activity detection."""
    
    def __init__(self):
        """Initialize the audio service."""
        self.config = AudioServiceConfig()
        self.neuralux_config = NeuraluxConfig()
        self.message_bus = MessageBusClient(self.neuralux_config)
        
        # Initialize backends
        self.stt_backend = STTBackend(self.config)
        self.tts_backend = TTSBackend(self.config)
        self.vad_backend = VADBackend(self.config) if self.config.vad_enabled else None
        
        self.app = FastAPI(
            title="Neuralux Audio Service",
            version="0.1.0",
            description="Speech-to-text, text-to-speech, and voice activity detection"
        )
        self._setup_routes()
        
        logger.info("Audio service initialized", config=self.config.model_dump())
    
    async def startup(self):
        """Start the audio service."""
        logger.info("Starting audio service")
        
        # Create necessary directories
        self.config.models_dir.mkdir(parents=True, exist_ok=True)
        self.config.stt_models_dir.mkdir(parents=True, exist_ok=True)
        self.config.tts_models_dir.mkdir(parents=True, exist_ok=True)
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load models in background to avoid blocking startup
        asyncio.create_task(self._load_models_async())
        
        # Connect to message bus
        await self.connect_to_message_bus()
        
        logger.info("Audio service started successfully")
    
    async def _load_models_async(self):
        """Load models asynchronously."""
        try:
            logger.info("Loading models in background")
            
            # Load STT model
            try:
                self.stt_backend.load_model()
            except Exception as e:
                logger.warning("STT model loading failed", error=str(e))
            
            # Load TTS model
            try:
                self.tts_backend.load_model()
            except Exception as e:
                logger.warning("TTS model loading failed", error=str(e))
            
            # Load VAD model
            if self.vad_backend:
                try:
                    self.vad_backend.load_model()
                except Exception as e:
                    logger.warning("VAD model loading failed", error=str(e))
            
            logger.info("Model loading completed")
        except Exception as e:
            logger.error("Error during model loading", error=str(e))
    
    async def shutdown(self):
        """Shutdown the audio service."""
        logger.info("Shutting down audio service")
        await self.disconnect_from_message_bus()
        logger.info("Audio service stopped")
    
    async def connect_to_message_bus(self):
        """Connect to NATS message bus and register handlers."""
        await self.message_bus.connect()
        
        prefix = self.config.nats_subject_prefix
        
        # STT handler
        async def _stt_handler(data: dict) -> dict:
            try:
                request = STTRequest(**data)
                result = self.stt_backend.transcribe(
                    audio_path=request.audio_path,
                    audio_data=request.audio_data,
                    language=request.language,
                    task=request.task,
                    vad_filter=request.vad_filter,
                    word_timestamps=request.word_timestamps,
                    temperature=request.temperature
                )
                return result
            except Exception as e:
                logger.error("STT request failed", error=str(e))
                return {"error": str(e)}
        
        # TTS handler
        async def _tts_handler(data: dict) -> dict:
            try:
                request = TTSRequest(**data)
                result = self.tts_backend.synthesize(
                    text=request.text,
                    voice=request.voice,
                    speed=request.speed,
                    output_format=request.output_format,
                    sample_rate=request.sample_rate
                )
                return result
            except Exception as e:
                logger.error("TTS request failed", error=str(e))
                return {"error": str(e)}
        
        # VAD handler
        async def _vad_handler(data: dict) -> dict:
            if not self.vad_backend:
                return {"error": "VAD is disabled"}
            try:
                request = VADRequest(**data)
                result = self.vad_backend.detect(
                    audio_path=request.audio_path,
                    audio_data=request.audio_data,
                    threshold=request.threshold
                )
                return result
            except Exception as e:
                logger.error("VAD request failed", error=str(e))
                return {"error": str(e)}
        
        # Info handler
        async def _info_handler(_data: dict) -> dict:
            info = AudioServiceInfo(
                models={
                    "stt": self.stt_backend.get_model_info(),
                    "tts": self.tts_backend.get_model_info(),
                    "vad": self.vad_backend.get_model_info() if self.vad_backend else None
                }
            )
            return info.model_dump()
        
        # Register handlers
        await self.message_bus.reply_handler(f"{prefix}.stt", _stt_handler)
        await self.message_bus.reply_handler(f"{prefix}.tts", _tts_handler)
        await self.message_bus.reply_handler(f"{prefix}.vad", _vad_handler)
        await self.message_bus.reply_handler(f"{prefix}.info", _info_handler)
        
        logger.info("Audio service connected to NATS and handlers registered")
    
    async def disconnect_from_message_bus(self):
        """Disconnect from NATS message bus."""
        await self.message_bus.disconnect()
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def read_root():
            """Root endpoint."""
            return {
                "service": "audio_service",
                "version": "0.1.0",
                "status": "running"
            }
        
        @self.app.get("/info")
        async def get_info() -> AudioServiceInfo:
            """Get service information."""
            return AudioServiceInfo(
                models={
                    "stt": self.stt_backend.get_model_info(),
                    "tts": self.tts_backend.get_model_info(),
                    "vad": self.vad_backend.get_model_info() if self.vad_backend else None
                }
            )
        
        @self.app.post("/stt/model")
        async def set_stt_model(name: str):
            """Switch STT model by name (e.g., tiny, base, small, medium, large)."""
            try:
                try:
                    await self.message_bus.publish("ai.audio.reload.events", {"event": "start", "kind": "stt", "model": name})
                except Exception:
                    pass
                self.config.stt_model = name
                # Reload backend
                self.stt_backend.unload_model()
                self.stt_backend.load_model()
                try:
                    await self.message_bus.publish("ai.audio.reload.events", {"event": "done", "kind": "stt", "model": name})
                except Exception:
                    pass
                return {"status": "ok", "stt_model": name}
            except Exception as e:
                try:
                    await self.message_bus.publish("ai.audio.reload.events", {"event": "error", "kind": "stt", "model": name, "error": str(e)})
                except Exception:
                    pass
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/stt", response_model=STTResponse)
        async def speech_to_text(request: STTRequest) -> STTResponse:
            """Convert speech to text."""
            try:
                result = self.stt_backend.transcribe(
                    audio_path=request.audio_path,
                    audio_data=request.audio_data,
                    language=request.language,
                    task=request.task,
                    vad_filter=request.vad_filter,
                    word_timestamps=request.word_timestamps,
                    temperature=request.temperature
                )
                return STTResponse(**result)
            except Exception as e:
                logger.error("STT request failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/stt/file")
        async def speech_to_text_file(
            file: UploadFile = File(...),
            language: str = None,
            vad_filter: bool = True
        ) -> STTResponse:
            """Convert uploaded audio file to text."""
            try:
                # Save uploaded file to temp location
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    content = await file.read()
                    f.write(content)
                    temp_path = f.name
                
                result = self.stt_backend.transcribe(
                    audio_path=temp_path,
                    language=language,
                    vad_filter=vad_filter
                )
                
                # Cleanup
                Path(temp_path).unlink()
                
                return STTResponse(**result)
            except Exception as e:
                logger.error("STT file request failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/tts", response_model=TTSResponse)
        async def text_to_speech(request: TTSRequest) -> TTSResponse:
            """Convert text to speech."""
            try:
                result = self.tts_backend.synthesize(
                    text=request.text,
                    voice=request.voice,
                    speed=request.speed,
                    output_format=request.output_format,
                    sample_rate=request.sample_rate
                )
                return TTSResponse(**result)
            except Exception as e:
                logger.error("TTS request failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/tts/audio")
        async def text_to_speech_audio(request: TTSRequest):
            """Convert text to speech and return audio file."""
            try:
                result = self.tts_backend.synthesize(
                    text=request.text,
                    voice=request.voice,
                    speed=request.speed,
                    output_format=request.output_format,
                    sample_rate=request.sample_rate
                )
                
                # Decode base64 audio
                import base64
                audio_bytes = base64.b64decode(result["audio_data"])
                
                return Response(
                    content=audio_bytes,
                    media_type=f"audio/{result['format']}",
                    headers={
                        "Content-Disposition": f'attachment; filename="speech.{result["format"]}"'
                    }
                )
            except Exception as e:
                logger.error("TTS audio request failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/vad", response_model=VADResponse)
        async def voice_activity_detection(request: VADRequest) -> VADResponse:
            """Detect voice activity in audio."""
            if not self.vad_backend:
                raise HTTPException(status_code=501, detail="VAD is disabled")
            
            try:
                result = self.vad_backend.detect(
                    audio_path=request.audio_path,
                    audio_data=request.audio_data,
                    threshold=request.threshold
                )
                return VADResponse(**result)
            except Exception as e:
                logger.error("VAD request failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))


# Create service instance
service = AudioService()


if __name__ == "__main__":
    import uvicorn
    
    setup_logging("audio_service")
    
    # Setup event handlers
    service.app.add_event_handler("startup", service.startup)
    service.app.add_event_handler("shutdown", service.shutdown)
    
    # Run the service
    uvicorn.run(
        service.app,
        host=service.config.host,
        port=service.config.service_port,
        log_level="info"
    )

