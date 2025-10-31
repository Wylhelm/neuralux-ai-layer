from pydantic import BaseModel, Field
from typing import Literal, Dict, Any
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class BaseEvent(BaseModel):
    """Base model for all temporal events."""
    event_id: str = Field(default_factory=generate_uuid)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str

class CommandEvent(BaseEvent):
    """An event representing an executed shell command."""
    event_type: Literal["command"] = "command"
    command: str
    cwd: str
    exit_code: int
    user: str

class FileEvent(BaseEvent):
    """An event representing a change in the filesystem."""
    event_type: Literal["file"] = "file"
    path: str
    change_type: Literal["created", "deleted", "modified", "moved"]
    is_directory: bool
    user: str

class AppFocusEvent(BaseEvent):
    """An event representing the active application window."""
    event_type: Literal["app_focus"] = "app_focus"
    app_name: str
    window_title: str
    user: str

class SystemSnapshotEvent(BaseEvent):
    """A periodic snapshot of system state."""
    event_type: Literal["system_snapshot"] = "system_snapshot"
    active_app_name: str
    active_window_title: str
    running_processes: list[str]
    cpu_usage: float
    memory_usage: float
