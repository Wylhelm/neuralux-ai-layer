"""Pydantic models for vision service."""

from pydantic import BaseModel
from typing import Optional, List


class OCRRequest(BaseModel):
    image_path: Optional[str] = None
    image_bytes_b64: Optional[str] = None
    language: Optional[str] = None


class OCRResponse(BaseModel):
    text: str
    confidence: Optional[float] = None
    words: Optional[List[str]] = None


