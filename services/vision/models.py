"""Pydantic models for vision service."""

from pydantic import BaseModel, Field
from typing import Optional, List


class OCRRequest(BaseModel):
    image_path: Optional[str] = None
    image_bytes_b64: Optional[str] = None
    language: Optional[str] = None


class OCRResponse(BaseModel):
    text: str
    confidence: Optional[float] = None
    words: Optional[List[str]] = None


class ImageGenRequest(BaseModel):
    """Request to generate an image from a text prompt."""
    prompt: str = Field(..., description="Text description of the image to generate")
    negative_prompt: Optional[str] = Field(None, description="What to avoid in the image")
    width: int = Field(1024, description="Image width in pixels", ge=256, le=2048)
    height: int = Field(1024, description="Image height in pixels", ge=256, le=2048)
    num_inference_steps: int = Field(4, description="Number of denoising steps", ge=1, le=100)
    guidance_scale: float = Field(7.5, description="How closely to follow the prompt", ge=0.0, le=20.0)
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    model: str = Field("flux-schnell", description="Model to use: flux-schnell, flux-dev, sdxl-lightning")


class ImageGenResponse(BaseModel):
    """Response from image generation."""
    image_bytes_b64: str = Field(..., description="Generated image as base64-encoded PNG")
    prompt: str = Field(..., description="The prompt that was used")
    model: str = Field(..., description="The model that was used")
    seed: Optional[int] = Field(None, description="The seed that was used (if any)")
    width: int = Field(..., description="Image width")
    height: int = Field(..., description="Image height")


class ModelInfoResponse(BaseModel):
    """Information about available and loaded models."""
    loaded: bool
    current_model: Optional[str] = None
    device: str
    cuda_available: bool
    available_models: List[str] = ["flux-schnell", "flux-dev", "sdxl-lightning"]


