"""Vision service main entry point (skeleton)."""

import sys
from pathlib import Path
import structlog
from fastapi import FastAPI

# Add common package to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.logger import setup_logging
from neuralux.messaging import MessageBusClient

from config import VisionServiceConfig
from models import OCRRequest, OCRResponse


logger = structlog.get_logger(__name__)


class VisionService:
    def __init__(self) -> None:
        self.config = VisionServiceConfig()
        self.neuralux_config = NeuraluxConfig()
        self.message_bus = MessageBusClient(self.neuralux_config)

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
                _ = OCRRequest(**data)
                # Placeholder implementation
                return OCRResponse(text="(vision skeleton: OCR not implemented)").model_dump()
            except Exception as e:
                return {"error": str(e)}

        async def _info_handler(_data: dict) -> dict:
            return {"service": self.config.service_name, "version": "0.1.0", "status": "running"}

        await self.message_bus.reply_handler(f"{prefix}.ocr", _ocr_handler)
        await self.message_bus.reply_handler(f"{prefix}.info", _info_handler)

        logger.info("Vision service connected to NATS and handlers registered")

    async def disconnect_from_message_bus(self) -> None:
        await self.message_bus.disconnect()

    def _setup_routes(self) -> None:
        @self.app.get("/")
        async def read_root():
            return {"service": self.config.service_name, "version": "0.1.0", "status": "running"}

        @self.app.post("/ocr")
        async def ocr(request: OCRRequest) -> OCRResponse:
            # Placeholder HTTP endpoint
            return OCRResponse(text="(vision skeleton: OCR not implemented)")


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


