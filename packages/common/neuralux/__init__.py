"""
Neuralux AI Layer - Common Package

Shared utilities and base classes for all Neuralux services.
"""

__version__ = "0.1.0"
__author__ = "Neuralux Team"

# Core components
from .config import NeuraluxConfig
from .messaging import MessageBusClient

# Conversation intelligence
from .conversation import (
    ConversationContext,
    ConversationManager,
    ConversationTurn,
    ActionResult,
    ActionType,
    ReferenceResolver,
)

from .orchestrator import (
    Action,
    ActionStatus,
    ActionOrchestrator,
)

from .action_planner import ActionPlanner

from .conversation_handler import ConversationHandler

from .file_ops import (
    FileOperations,
    PathExpander,
)

# Legacy session store (for backward compatibility)
from .memory import SessionStore, default_session_id

__all__ = [
    "NeuraluxConfig",
    "MessageBusClient",
    "ConversationContext",
    "ConversationManager",
    "ConversationTurn",
    "ActionResult",
    "ActionType",
    "ReferenceResolver",
    "Action",
    "ActionStatus",
    "ActionOrchestrator",
    "ActionPlanner",
    "ConversationHandler",
    "FileOperations",
    "PathExpander",
    "SessionStore",
    "default_session_id",
]

