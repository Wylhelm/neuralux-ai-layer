"""Vision service main entry point (skeleton)."""

import sys
from pathlib import Path
import structlog
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
from collections import deque

# Add common package to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.logger import setup_logging
from neuralux.messaging import MessageBusClient

from config import VisionServiceConfig
from models import OCRRequest, OCRResponse, ImageGenRequest, ImageGenResponse, ModelInfoResponse
from ocr_backend import OCRProcessor
from image_gen_backend import ImageGenerationBackend, set_download_progress_callback
from typing import Optional
import base64
from io import BytesIO
from PIL import Image


logger = structlog.get_logger(__name__)

# Global progress message queue for streaming
progress_messages = deque(maxlen=100)

def progress_callback(message: str):
    """Callback for progress updates."""
    progress_messages.append(message)


class VisionService:
    def __init__(self) -> None:
        self.config = VisionServiceConfig()
        self.neuralux_config = NeuraluxConfig()
        self.message_bus = MessageBusClient(self.neuralux_config)
        self.ocr = OCRProcessor()
        self.image_gen = ImageGenerationBackend()
        
        # Set progress callback
        set_download_progress_callback(progress_callback)

        self.app = FastAPI(
            title="Neuralux Vision Service",
            version="0.1.0",
            description="OCR, image generation, and vision capabilities",
        )
        self._setup_routes()

    async def connect_to_message_bus(self) -> None:
        await self.message_bus.connect()
        
        # Start background task for automatic model unloading
        asyncio.create_task(self._unload_inactive_models())

        prefix = self.config.nats_subject_prefix

        async def _ocr_handler(data: dict) -> dict:
            logger.info("Received OCR request")
            try:
                req = OCRRequest(**data)
                img: Optional[Image.Image] = None
                if req.image_path:
                    try:
                        img = Image.open(req.image_path)
                    except Exception as e:
                        return {"error": f"Failed to open image: {e}"}
                elif req.image_bytes_b64:
                    try:
                        raw = base64.b64decode(req.image_bytes_b64)
                        img = Image.open(BytesIO(raw))
                    except Exception as e:
                        return {"error": f"Invalid image bytes: {e}"}
                else:
                    return {"error": "No image provided"}

                logger.info("Calling OCR backend")
                result = self.ocr.run(img, language=req.language)
                logger.info("OCR backend returned", result_keys=list(result.keys()) if isinstance(result, dict) else None)
                if result.get("error"):
                    return {"error": result.get("error")}
                response = OCRResponse(
                    text=result.get("text", ""),
                    confidence=result.get("confidence"),
                    words=result.get("words") or None,
                ).model_dump()
                # Also publish the result for listeners
                try:
                    await self.message_bus.publish(f"{prefix}.ocr.result", {"request": req.model_dump(), "response": response})
                except Exception:
                    pass
                return response
            except Exception as e:
                logger.error("OCR handler failed", error=str(e))
                return {"error": str(e)}

        async def _image_gen_handler(data: dict) -> dict:
            try:
                req = ImageGenRequest(**data)
                
                # Generate image
                image = self.image_gen.generate(
                    prompt=req.prompt,
                    negative_prompt=req.negative_prompt,
                    width=req.width,
                    height=req.height,
                    num_inference_steps=req.num_inference_steps,
                    guidance_scale=req.guidance_scale,
                    seed=req.seed,
                )
                
                # Save to temp file to avoid NATS payload size limits
                import tempfile
                import time
                temp_dir = tempfile.gettempdir()
                timestamp = int(time.time() * 1000000)
                image_path = f"{temp_dir}/neuralux_img_{timestamp}.png"
                image.save(image_path, format="PNG")
                
                # Return path instead of base64 for NATS (avoids payload limit)
                response = {
                    "image_path": image_path,
                    "prompt": req.prompt,
                    "model": self.image_gen.current_model or req.model,
                    "seed": req.seed,
                    "width": image.width,
                    "height": image.height,
                }
                
                # Publish result event
                try:
                    await self.message_bus.publish(f"{prefix}.imagegen.result", {"request": req.model_dump(), "response": response})
                except Exception:
                    pass
                
                return response
            except Exception as e:
                logger.error("Image generation failed", error=str(e))
                return {"error": str(e)}

        async def _model_info_handler(_data: dict) -> dict:
            info = self.image_gen.get_model_info()
            return ModelInfoResponse(**info).model_dump()

        async def _info_handler(_data: dict) -> dict:
            return {"service": self.config.service_name, "version": "0.1.0", "status": "running"}

        await self.message_bus.reply_handler(f"{prefix}.ocr.request", _ocr_handler)
        await self.message_bus.reply_handler(f"{prefix}.imagegen.request", _image_gen_handler)
        await self.message_bus.reply_handler(f"{prefix}.imagegen.model_info", _model_info_handler)
        await self.message_bus.reply_handler(f"{prefix}.info", _info_handler)

        logger.info("Vision service connected to NATS and handlers registered")

    async def disconnect_from_message_bus(self) -> None:
        await self.message_bus.disconnect()
    
    async def _unload_inactive_models(self):
        """Background task to unload inactive models."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                if self.image_gen.should_unload():
                    logger.info("Unloading inactive image generation model")
                    self.image_gen.unload_model()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in model unload task", error=str(e))

    def _setup_routes(self) -> None:
        @self.app.get("/")
        async def read_root():
            return {"service": self.config.service_name, "version": "0.1.0", "status": "running"}

        @self.app.post("/v1/ocr")
        async def ocr(request: OCRRequest) -> OCRResponse:
            try:
                img: Optional[Image.Image] = None
                if request.image_path:
                    img = Image.open(request.image_path)
                elif request.image_bytes_b64:
                    raw = base64.b64decode(request.image_bytes_b64)
                    img = Image.open(BytesIO(raw))
                else:
                    raise HTTPException(status_code=400, detail="No image provided")
                result = self.ocr.run(img, language=request.language)
                if result.get("error"):
                    raise HTTPException(status_code=500, detail=result.get("error"))
                return OCRResponse(
                    text=result.get("text", ""),
                    confidence=result.get("confidence"),
                    words=result.get("words") or None,
                )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/v1/generate-image")
        async def generate_image(request: ImageGenRequest) -> ImageGenResponse:
            """Generate an image from a text prompt using Flux or other models."""
            try:
                # Generate image
                image = self.image_gen.generate(
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    width=request.width,
                    height=request.height,
                    num_inference_steps=request.num_inference_steps,
                    guidance_scale=request.guidance_scale,
                    seed=request.seed,
                )
                
                # Convert to base64
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                return ImageGenResponse(
                    image_bytes_b64=image_b64,
                    prompt=request.prompt,
                    model=self.image_gen.current_model or request.model,
                    seed=request.seed,
                    width=image.width,
                    height=image.height,
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Image generation failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/v1/model-info")
        async def get_model_info() -> ModelInfoResponse:
            """Get information about the current image generation model."""
            info = self.image_gen.get_model_info()
            return ModelInfoResponse(**info)

        @self.app.post("/v1/load-model")
        async def load_model(model_name: str):
            """Load a specific image generation model."""
            try:
                self.image_gen.load_model(model_name)
                return {"status": "ok", "model": model_name}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/v1/progress-stream")
        async def progress_stream():
            """Stream progress messages as Server-Sent Events."""
            async def event_generator():
                last_sent_count = 0
                try:
                    while True:
                        # Send new messages
                        current_count = len(progress_messages)
                        if current_count > last_sent_count:
                            for i in range(last_sent_count, current_count):
                                msg = list(progress_messages)[i]
                                yield f"data: {msg}\n\n"
                            last_sent_count = current_count
                        
                        await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    pass
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )


# Create service instance
service = VisionService()


if __name__ == "__main__":
    import uvicorn

    setup_logging("vision_service")

    async def startup():
        await service.connect_to_message_bus()

    async def shutdown():
        await service.disconnect_from_message_bus()

    service.app.add_event_handler("startup", startup)
    service.app.add_event_handler("shutdown", shutdown)

    uvicorn.run(service.app, host=service.config.host, port=service.config.service_port, log_level="info")
