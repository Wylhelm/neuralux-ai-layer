"""Fuzzy search for overlay suggestions.

Provides best-effort fuzzy ranking using rapidfuzz when available,
with a simple substring fallback otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Suggestion:
    title: str
    subtitle: str
    payload: dict


def _score(query: str, text: str) -> int:
    q = query.strip()
    if not q:
        return 0
    try:
        # Prefer rapidfuzz if available
        from rapidfuzz import fuzz  # type: ignore

        return int(fuzz.token_set_ratio(q, text))
    except Exception:
        # Simple contains scoring fallback
        text_l = text.lower()
        q_l = q.lower()
        if q_l in text_l:
            return min(100, 50 + len(q_l))
        return 0


def suggest(query: str, max_results: int = 7, threshold: int = 40) -> List[Suggestion]:
    """Return ranked overlay suggestions for a query.

    Suggestions include:
    - Ask AI (LLM)
    - Search files (filesystem service)
    - Check health (system health summary)
    """

    items: List[Tuple[str, str, dict]] = [
        (
            f"Ask AI: {query}",
            "Get a command suggestion from the assistant",
            {"type": "llm_query", "query": query},
        ),
        (
            f"Search files: {query}",
            "Find documents matching your text",
            {"type": "file_search", "query": query},
        ),
        (
            "Check system health",
            "Show current CPU, memory, disks and alerts",
            {"type": "health_summary"},
        ),
        (
            "OCR active window",
            "Recognize text from the current active window",
            {"type": "overlay_command", "command": "/ocr window"},
        ),
        (
            "OCR and continue chat",
            "Capture window text then enter follow-up chat",
            {"type": "sequence", "commands": ["/ocr window", "/start_chat"]},
        ),
    ]

    scored = [
        ( _score(query, t + " " + s), t, s, p )
        for (t, s, p) in items
    ]
    scored.sort(key=lambda x: x[0], reverse=True)

    # If nothing passes threshold, still show defaults, but keep ordering
    results: List[Suggestion] = []
    for score, title, subtitle, payload in scored:
        if score >= threshold or len(results) < 3:
            results.append(Suggestion(title=title, subtitle=subtitle, payload=payload))
        if len(results) >= max_results:
            break
    return results


