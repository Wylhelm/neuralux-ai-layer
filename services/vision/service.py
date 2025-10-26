"""Vision service main entry point (skeleton)."""

import sys
from pathlib import Path
import structlog
from fastapi import FastAPI, UploadFile, File, HTTPException

# Add common package to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.logger import setup_logging
from neuralux.messaging import MessageBusClient

from config import VisionServiceConfig
from models import OCRRequest, OCRResponse
from ocr_backend import OCRProcessor
from typing import Optional
import base64
from io import BytesIO
from PIL import Image


logger = structlog.get_logger(__name__)


class VisionService:
    def __init__(self) -> None:
        self.config = VisionServiceConfig()
        self.neuralux_config = NeuraluxConfig()
        self.message_bus = MessageBusClient(self.neuralux_config)
        self.ocr = OCRProcessor()

        self.app = FastAPI(
            title="Neuralux Vision Service",
            version="0.1.0",
            description="OCR and basic vision capabilities (skeleton)",
        )
        self._setup_routes()

    async def connect_to_message_bus(self) -> None:
        await self.message_bus.connect()

        prefix = self.config.nats_subject_prefix

        async def _ocr_handler(data: dict) -> dict:
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

                result = self.ocr.run(img, language=req.language)
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
                return {"error": str(e)}

        async def _info_handler(_data: dict) -> dict:
            return {"service": self.config.service_name, "version": "0.1.0", "status": "running"}

        await self.message_bus.reply_handler(f"{prefix}.ocr.request", _ocr_handler)
        await self.message_bus.reply_handler(f"{prefix}.info", _info_handler)

        logger.info("Vision service connected to NATS and handlers registered")

    async def disconnect_from_message_bus(self) -> None:
        await self.message_bus.disconnect()

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


