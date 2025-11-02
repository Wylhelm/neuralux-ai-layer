"""Specialized result cards for different action types."""

from .command_card import CommandOutputCard
from .document_card import DocumentQueryCard
from .web_card import WebSearchCard
from .image_card import ImageGenerationCard
from .llm_card import LLMGenerationCard
from .system_command_card import SystemCommandCard
from .music_card import MusicCard

__all__ = [
    "CommandOutputCard",
    "DocumentQueryCard",
    "WebSearchCard",
    "ImageGenerationCard",
    "LLMGenerationCard",
    "SystemCommandCard",
    "MusicCard",
]
