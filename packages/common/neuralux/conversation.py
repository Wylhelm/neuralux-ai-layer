"""Enhanced conversation context manager with action tracking and reference resolution."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path
from enum import Enum

import redis
import structlog

from .config import NeuraluxConfig

logger = structlog.get_logger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be tracked."""
    # AI-specific actions (not shell commands)
    LLM_GENERATE = "llm_generate"
    IMAGE_GENERATE = "image_generate"
    IMAGE_SAVE = "image_save"
    MUSIC_GENERATE = "music_generate"
    MUSIC_SAVE = "music_save"
    OCR_CAPTURE = "ocr_capture"
    DOCUMENT_QUERY = "document_query"
    WEB_SEARCH = "web_search"
    
    # Generic command execution (for all file/system operations)
    COMMAND_EXECUTE = "command_execute"
    SYSTEM_COMMAND = "system_command"


@dataclass
class ActionResult:
    """Result of an executed action."""
    action_type: ActionType
    timestamp: float
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type.value,
            "timestamp": self.timestamp,
            "success": self.success,
            "details": self.details,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActionResult:
        """Create from dictionary."""
        return cls(
            action_type=ActionType(data.get("action_type", "llm_generate")),
            timestamp=data.get("timestamp", time.time()),
            success=data.get("success", False),
            details=data.get("details", {}),
            error=data.get("error"),
        )


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float
    action_result: Optional[ActionResult] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "action_result": self.action_result.to_dict() if self.action_result else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationTurn:
        """Create from dictionary."""
        action_data = data.get("action_result")
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", time.time()),
            action_result=ActionResult.from_dict(action_data) if action_data else None,
        )


@dataclass
class ConversationContext:
    """Rich conversation context with action tracking."""
    
    # Basic context
    session_id: str
    user_id: str
    
    # Conversation history
    turns: List[ConversationTurn] = field(default_factory=list)
    
    # Context variables (for reference resolution)
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # Working directory
    working_directory: str = ""
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def add_turn(self, role: str, content: str, action_result: Optional[ActionResult] = None):
        """Add a conversation turn."""
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=time.time(),
            action_result=action_result,
        )
        self.turns.append(turn)
        self.updated_at = time.time()
    
    def set_variable(self, key: str, value: Any):
        """Set a context variable."""
        self.variables[key] = value
        self.updated_at = time.time()
        logger.debug("context_variable_set", key=key, value=value)
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.variables.get(key, default)
    
    def get_last_action_result(self, action_type: Optional[ActionType] = None) -> Optional[ActionResult]:
        """Get the last action result, optionally filtered by type."""
        for turn in reversed(self.turns):
            if turn.action_result:
                if action_type is None or turn.action_result.action_type == action_type:
                    return turn.action_result
        return None
    
    def get_chat_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get chat history in OpenAI format for LLM."""
        messages = []
        turns = self.turns[-limit:] if limit else self.turns
        for turn in turns:
            messages.append({
                "role": turn.role,
                "content": turn.content,
            })
        return messages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "turns": [turn.to_dict() for turn in self.turns],
            "variables": self.variables,
            "working_directory": self.working_directory,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationContext:
        """Create from dictionary."""
        turns_data = data.get("turns", [])
        turns = [ConversationTurn.from_dict(t) for t in turns_data if isinstance(t, dict)]
        
        return cls(
            session_id=data.get("session_id", "default"),
            user_id=data.get("user_id", "default"),
            turns=turns,
            variables=data.get("variables", {}),
            working_directory=data.get("working_directory", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class ConversationManager:
    """Manages conversation contexts with Redis backend."""
    
    def __init__(self, config: Optional[NeuraluxConfig] = None, ttl_seconds: int = 24 * 3600):
        """Initialize conversation manager."""
        self.config = config or NeuraluxConfig()
        self.ttl_seconds = ttl_seconds
        self._redis = redis.Redis.from_url(
            self.config.redis_url,
            db=self.config.redis_db,
            decode_responses=True
        )
    
    def _key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"nlx:conversation:{session_id}"
    
    def load(self, session_id: str, user_id: str = "default") -> ConversationContext:
        """Load conversation context from Redis."""
        raw = self._redis.get(self._key(session_id))
        if not raw:
            # Create new context
            ctx = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                working_directory=str(Path.home()),
            )
            logger.debug("created_new_conversation_context", session_id=session_id)
            return ctx
        
        try:
            data = json.loads(raw)
            ctx = ConversationContext.from_dict(data)
            logger.debug("loaded_conversation_context", session_id=session_id, turns=len(ctx.turns))
            return ctx
        except Exception as e:
            logger.error("failed_to_load_conversation", session_id=session_id, error=str(e))
            # Return fresh context on error
            return ConversationContext(
                session_id=session_id,
                user_id=user_id,
                working_directory=str(Path.home()),
            )
    
    def save(self, context: ConversationContext):
        """Save conversation context to Redis."""
        try:
            context.updated_at = time.time()
            data = context.to_dict()
            payload = json.dumps(data)
            self._redis.setex(self._key(context.session_id), self.ttl_seconds, payload)
            logger.debug("saved_conversation_context", session_id=context.session_id, turns=len(context.turns))
        except Exception as e:
            logger.error("failed_to_save_conversation", session_id=context.session_id, error=str(e))
    
    def reset(self, session_id: str):
        """Reset conversation context."""
        self._redis.delete(self._key(session_id))
        logger.info("reset_conversation_context", session_id=session_id)
    
    def list_sessions(self, pattern: str = "nlx:conversation:*") -> List[str]:
        """List all session IDs."""
        keys = self._redis.keys(pattern)
        return [key.replace("nlx:conversation:", "") for key in keys]


class ReferenceResolver:
    """Resolves references in user input like 'it', 'that', 'the image', etc."""
    
    # Pronouns and references that need resolution
    PRONOUNS = ["it", "this", "that", "these", "those", "them"]
    
    # Common phrases that need resolution
    PHRASES = [
        "the image",
        "the file",
        "the text",
        "the summary",
        "the result",
        "the output",
        "last image",
        "last file",
        "previous result",
        "that image",
        "that file",
    ]
    
    @staticmethod
    def needs_resolution(text: str) -> bool:
        """Check if text contains references that need resolution."""
        lower = text.lower()
        
        # Check for pronouns at word boundaries
        for pronoun in ReferenceResolver.PRONOUNS:
            if f" {pronoun} " in f" {lower} " or lower.startswith(f"{pronoun} "):
                return True
        
        # Check for common phrases
        for phrase in ReferenceResolver.PHRASES:
            if phrase in lower:
                return True
        
        return False
    
    @staticmethod
    def resolve(text: str, context: ConversationContext) -> tuple[str, Dict[str, Any]]:
        """
        Resolve references in text using conversation context.
        
        Returns:
            (resolved_text, resolved_values)
        """
        resolved_values = {}
        resolved_text = text
        
        lower = text.lower()
        
        # Check what we have in context
        last_image = context.get_variable("last_generated_image")
        last_file = context.get_variable("last_created_file")
        last_ocr_text = context.get_variable("last_ocr_text")
        last_generated_text = context.get_variable("last_generated_text")
        
        # Resolve image references
        if last_image and any(ref in lower for ref in ["the image", "that image", "it", "this"]):
            if "image" in lower or context.get_last_action_result(ActionType.IMAGE_GENERATE):
                resolved_values["image_path"] = last_image
                # Don't replace text, just track the resolution
        
        # Resolve file references
        if last_file:
            created_files = context.get_variable("created_files", [])
            if isinstance(created_files, list) and created_files:
                last_file = created_files[-1]
            
            if any(ref in lower for ref in ["the file", "that file", "it", "this"]):
                if "file" in lower:
                    resolved_values["file_path"] = last_file
        
        # Resolve text/content references
        if last_ocr_text and any(ref in lower for ref in ["the text", "ocr text", "that text", "it"]):
            resolved_values["ocr_text"] = last_ocr_text
        
        if last_generated_text and any(ref in lower for ref in ["the summary", "the result", "that"]):
            resolved_values["generated_text"] = last_generated_text
        
        return resolved_text, resolved_values
