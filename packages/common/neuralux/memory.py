"""Redis-backed session memory for overlay/CLI shared context and chat history."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import redis  # type: ignore
import json
from pathlib import Path

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

    # --- Conversation archives (multiple sessions per user) ---
    def _archive_key(self, user_id: str) -> str:
        return f"nlx:archive:{user_id}"

    def archive(self, user_id: str, data: Dict[str, Any], max_keep: int = 50) -> None:
        """Append current conversation data to the user's archive list.
        Stores a compact record with id(=updated_at timestamp), context, and chat history.
        """
        payload = {
            "id": int(data.get("updated_at") or int(time.time())),
            "updated_at": int(time.time()),
            "context_text": data.get("context_text", ""),
            "context_kind": data.get("context_kind", ""),
            "chat_history": data.get("chat_history", []) or [],
        }
        self._redis.lpush(self._archive_key(user_id), json.dumps(payload))
        # Trim to last N entries
        self._redis.ltrim(self._archive_key(user_id), 0, max_keep - 1)

    def list_archives(self, user_id: str, start: int = 0, count: int = 10) -> list[dict]:
        items = self._redis.lrange(self._archive_key(user_id), start, start + count - 1) or []
        out = []
        for raw in items:
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            # Build a small summary for display
            title = ""
            for m in obj.get("chat_history", []):
                if (m.get("role") or "").lower() == "user":
                    title = (m.get("content") or "").strip()
                    if title:
                        break
            obj["title"] = title[:80]
            out.append(obj)
        return out

    def get_archive(self, user_id: str, archive_id: int) -> dict | None:
        items = self._redis.lrange(self._archive_key(user_id), 0, -1) or []
        for raw in items:
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if int(obj.get("id") or 0) == int(archive_id):
                return obj
        return None

    # Optional persistence of simple settings on disk (JSON)
    def load_settings(self, path: Path) -> Dict[str, Any]:
        try:
            if path.exists():
                return json.loads(path.read_text())
        except Exception:
            pass
        return {}

    def save_settings(self, path: Path, data: Dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2))
        except Exception:
            pass


def default_session_id() -> str:
    """Derive a default session id (per-user machine-local)."""
    import getpass, socket
    return f"{getpass.getuser()}@{socket.gethostname()}"


