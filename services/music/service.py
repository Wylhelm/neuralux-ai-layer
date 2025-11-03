import asyncio
import os
import time
from pathlib import Path
import sys
import structlog
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration
from scipy.io.wavfile import write as write_wav
import numpy as np
import gc

# Add project root to path to allow absolute imports from services
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.music.config import MusicServiceConfig

logger = structlog.get_logger(__name__)

class MusicGenerationService:
    def __init__(self, message_bus):
        self.message_bus = message_bus
        self.config = MusicServiceConfig()
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._last_used: float = 0.0  # Track last usage time
        self._unload_timeout: int = 300  # Unload after 5 minutes of inactivity
        
        # Ensure model directory exists
        self.model_path = Path(self.config.model_cache_dir)
        self.model_path.mkdir(parents=True, exist_ok=True)

    async def start(self):
        logger.info("Starting Music Generation Service (models will load on first use)...")
        await self.message_bus.subscribe("agent.music.generate", self._handle_music_generation_request)
        # Start background task for automatic model unloading
        asyncio.create_task(self._unload_inactive_model())

    async def _ensure_model_loaded(self):
        if self.model is None or self.processor is None:
            logger.info("Loading music generation model...", path=self.model_path)
            try:
                model_name = self.config.model_name
                self.processor = AutoProcessor.from_pretrained(model_name, cache_dir=self.model_path)
                self.model = MusicgenForConditionalGeneration.from_pretrained(model_name, cache_dir=self.model_path)
                self.model.to(self.device)
                logger.info("Music generation model loaded successfully.")
            except Exception as e:
                logger.error("Failed to load music generation model", error=str(e))
                raise
    
    def should_unload(self) -> bool:
        """Check if model should be unloaded due to inactivity."""
        if self.model is None:
            return False
        if self._last_used == 0.0:
            return False
        inactive_time = time.time() - self._last_used
        return inactive_time > self._unload_timeout
    
    async def _unload_inactive_model(self):
        """Background task to unload inactive model."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                if self.should_unload():
                    logger.info("Unloading inactive music generation model")
                    self.unload_model()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in model unload task", error=str(e))
    
    def unload_model(self) -> None:
        """Unload the current model."""
        if self.model is not None:
            logger.info("Unloading music generation model")
            del self.model
            self.model = None
            del self.processor
            self.processor = None
            self._last_used = 0.0
            # Force garbage collection and clear CUDA cache
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Music generation model unloaded")

    async def _handle_music_generation_request(self, payload):
        prompt = payload.get("prompt")
        duration = payload.get("duration", 30)
        user_id = payload.get("user_id")
        conversation_id = payload.get("conversation_id")

        if not prompt:
            return {"error": "Prompt is required for music generation."}

        logger.info("Generating music with prompt", prompt=prompt, duration=duration)

        try:
            if self.model is None or self.processor is None:
                await self._ensure_model_loaded()
                if self.model is None:
                    raise RuntimeError("Music generation model could not be loaded.")
            
            # Update usage time when model is used
            self._last_used = time.time()

            inputs = self.processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            ).to(self.device)

            audio_values = self.model.generate(**inputs)

            # Save the generated audio
            music_dir = Path(self.config.output_dir)
            music_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate a random filename
            import re
            safe_prompt = re.sub(r'[^\\w\\s-]', '', prompt)[:50]
            safe_prompt = re.sub(r'[-\\s]+', '_', safe_prompt)
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{safe_prompt}_{timestamp}.wav"
            file_path = music_dir / filename
            
            sampling_rate = self.model.config.audio_encoder.sampling_rate
            audio_numpy = audio_values[0, 0].cpu().numpy()
            
            # Ensure the audio data is in a valid format for WAV
            if np.issubdtype(audio_numpy.dtype, np.floating):
                audio_numpy = (audio_numpy * 32767).astype(np.int16)

            write_wav(file_path, sampling_rate, audio_numpy)

            logger.info("Music saved to file", path=str(file_path))

            response = {
                "type": "music_result",
                "file_path": str(file_path),
                "prompt": prompt,
            }
            await self.message_bus.publish(f"conversation.{conversation_id}", response)

        except Exception as e:
            logger.error("Music generation failed", error=str(e))
            error_response = {
                "type": "error",
                "content": f"Sorry, I couldn't generate the music: {e}",
            }
            await self.message_bus.publish(f"conversation.{conversation_id}", error_response)


if __name__ == "__main__":
    import asyncio
    from neuralux.messaging import MessageBusClient
    from neuralux.config import NeuraluxConfig

    async def main():
        config = NeuraluxConfig()
        message_bus = MessageBusClient(config)
        await message_bus.connect()
        
        service = MusicGenerationService(message_bus)
        await service.start()
        
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await message_bus.disconnect()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Music service shutting down.")
