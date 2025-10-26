"""Redis-backed session memory for overlay/CLI shared context and chat history."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import redis  # type: ignore

from .config import NeuraluxConfig


class SessionStore:
    """Simple Redis-backed session store with TTL.

    Data model:
    - key: nlx:session:{session_id}
    - value: JSON { context_text, context_kind, chat_history, updated_at }
    """

    def __init__(self, config: Optional[NeuraluxConfig] = None, ttl_seconds: int = 24 * 3600) -> None:
        self.config = config or NeuraluxConfig()
        self.ttl_seconds = int(ttl_seconds)
        self._redis = redis.Redis.from_url(self.config.redis_url, db=self.config.redis_db, decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"nlx:session:{session_id}"

    def load(self, session_id: str) -> Dict[str, Any]:
        raw = self._redis.get(self._key(session_id))
        if not raw:
            return {"context_text": "", "context_kind": "", "chat_history": []}
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
        data.setdefault("context_text", "")
        data.setdefault("context_kind", "")
        data.setdefault("chat_history", [])
        return data

    def save(self, session_id: str, data: Dict[str, Any]) -> None:
        data = dict(data or {})
        data["updated_at"] = int(time.time())
        payload = json.dumps(data)
        self._redis.setex(self._key(session_id), self.ttl_seconds, payload)

    def reset(self, session_id: str) -> None:
        self._redis.delete(self._key(session_id))


def default_session_id() -> str:
    """Derive a default session id (per-user machine-local)."""
    import getpass, socket
    return f"{getpass.getuser()}@{socket.gethostname()}"


