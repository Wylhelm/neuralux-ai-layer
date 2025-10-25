"""Configuration for the vision service."""

from pydantic_settings import BaseSettings


class VisionServiceConfig(BaseSettings):
    service_name: str = "vision_service"
    host: str = "0.0.0.0"
    service_port: int = 8005
    nats_subject_prefix: str = "ai.vision"

    class Config:
        env_prefix = "VISION_"
        case_sensitive = False


