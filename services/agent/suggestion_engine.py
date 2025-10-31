"""LLM-backed suggestion engine for proactive agent."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import structlog


logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are the Neuralux Proactive Agent. You receive JSON describing a recent user command.
Your task is to suggest useful follow-up actions that would genuinely help the user.

Respond ONLY with JSON in the following format (no prose outside JSON):
{
  "suggestions": [
    {
      "id": "kebab-case-identifier",
      "title": "Short title",
      "message": "Helpful explanation of why this suggestion matters",
      "actions": [
        {"label": "Button label", "command": "command to run"}
      ]
    }
  ]
}

Guidelines:
- Return at most 2 suggestions; use an empty list if nothing is helpful.
- Prefer safe, non-destructive commands. Never suggest commands that delete or overwrite important data.
- Tailor the suggestion to the command context. Mention relevant files/paths when useful.
- If the original command failed (exit_code != 0), focus on remediation steps.
- Use absolute or clearly relative paths whenever possible.
"""


class AISuggestionEngine:
    """Generate proactive suggestions via the LLM service."""

    def __init__(
        self,
        nc,
        *,
        request_timeout: float = 3.0,
        max_suggestions: int = 2,
    ) -> None:
        self._nc = nc
        self._timeout = request_timeout
        self._max_suggestions = max_suggestions

    async def suggest_for_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return a single suggestion dict or None."""

        if not self._nc or not event_data:
            return None

        command_text = event_data.get("command")
        if not command_text:
            return None

        request_payload = self._build_request(event_data)

        try:
            response = await self._nc.request(
                "ai.llm.request",
                json.dumps(request_payload).encode(),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("llm_suggestion_timeout", command=command_text)
            return None
        except Exception as exc:  # pragma: no cover - best-effort logging
            logger.error("llm_suggestion_request_failed", error=str(exc))
            return None

        raw_response = self._decode_response(response)
        suggestions = self._parse_suggestions(raw_response)

        if not suggestions:
            return None

        # Limit and normalise actions to avoid surprises downstream
        first = suggestions[0]
        first.setdefault("actions", [])

        if isinstance(first["actions"], list):
            first["actions"] = [
                action
                for action in first["actions"]
                if isinstance(action, dict)
                and action.get("label")
                and action.get("command")
            ][:3]
        else:
            first["actions"] = []

        return first

    def _build_request(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Construct OpenAI-style request for the LLM service."""

        # Provide compact JSON to the model for clarity
        command_summary = json.dumps(event_data, ensure_ascii=False, indent=2)

        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Here is the command event JSON. Analyse it and respond with helpful"
                        " follow-up suggestions.\n\n" + command_summary
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 450,
        }

    def _decode_response(self, response) -> str:
        try:
            payload = json.loads(response.data.decode())
            content = payload.get("content")
            if isinstance(content, str):
                return content
            # Some services return list of choices
            if isinstance(content, list) and content:
                return content[0]
        except Exception:
            pass
        return response.data.decode()

    def _parse_suggestions(self, raw: str) -> List[Dict[str, Any]]:
        if not raw:
            return []

        content = raw.strip()

        # Remove optional markdown fences
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1]

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("llm_suggestion_parse_failed", snippet=content[:120])
            return []

        if isinstance(data, dict):
            suggestions = data.get("suggestions", [])
        elif isinstance(data, list):
            suggestions = data
        else:
            suggestions = []

        normalised = []
        for item in suggestions:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            message = item.get("message")
            suggestion_id = item.get("id")
            if not (title and message):
                continue
            if not suggestion_id:
                suggestion_id = self._slugify(title)
            normalised.append(
                {
                    "id": suggestion_id,
                    "title": title,
                    "message": message,
                    "actions": item.get("actions", []),
                }
            )

        return normalised[: self._max_suggestions]

    @staticmethod
    def _slugify(text: str) -> str:
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
        slug = slug.strip("-") or "suggestion"
        return slug[:60]

