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
    # If the user starts typing a slash command, offer command palette suggestions
    if (query or "").strip().startswith("/"):
        return _suggest_commands(query, max_results=max_results)

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
        (
            "Select region for OCR",
            "Drag to select a screen region to OCR",
            {"type": "overlay_command", "command": "/ocr select"},
        ),
        (
            "New conversation",
            "Clear memory and start fresh",
            {"type": "overlay_command", "command": "/fresh"},
        ),
        (
            "Conversation history",
            "Browse previous messages",
            {"type": "overlay_command", "command": "/history"},
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
        if score >= threshold or len(results) < 6:
            results.append(Suggestion(title=title, subtitle=subtitle, payload=payload))
        if len(results) >= max_results:
            break
    return results


def _suggest_commands(query: str, max_results: int = 12) -> List[Suggestion]:
    """Return fuzzy-matched command suggestions when typing '/'."""
    catalog: List[Tuple[str, str]] = [
        ("/start_chat", "Enter conversational mode with current context"),
        ("/fresh", "Start new conversation (clear memory)"),
        ("/history", "Show recent messages and archives"),
        ("/restore <id>", "Restore a previous session by id"),
        ("/ocr window", "OCR the active window"),
        ("/ocr select", "Select a region to OCR"),
        ("/ocr region x,y,w,h", "OCR a specific rectangle"),
        ("/web <query>", "Search the web"),
        ("/search <query>", "Search files semantically"),
        ("/health", "Show system health summary"),
        ("/tts toggle", "Toggle auto text-to-speech"),
        ("/voice", "Record 5s and transcribe to ask"),
        ("/approve", "Approve the pending action"),
        ("/cancel", "Cancel the pending action"),
        ("/copy", "Copy last OCR text to clipboard"),
        ("/summarize", "Summarize last OCR text"),
        ("/translate en|fr", "Translate last OCR text"),
        ("/extract", "Extract tables or key-values from OCR text"),
        ("/refresh", "Refresh suggestions"),
    ]

    q = (query or "").strip().lower()
    scored: List[Tuple[int, str, str]] = []
    for cmd, desc in catalog:
        hay = f"{cmd} {desc}"
        scored.append((_score(q, hay), cmd, desc))
    scored.sort(key=lambda x: x[0], reverse=True)

    out: List[Suggestion] = []
    for score, cmd, desc in scored:
        # Always show a reasonable number even if low-scoring when user just typed '/'
        if q in ("/", "") or score >= 30 or len(out) < 8:
            out.append(Suggestion(title=cmd, subtitle=desc, payload={"type": "overlay_command", "command": cmd.split()[0]}))
        if len(out) >= max_results:
            break
    return out


