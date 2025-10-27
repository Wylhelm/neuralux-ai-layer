"""Intent classification and routing for natural language inputs."""

import json
import re
from typing import Dict, Any, Optional, List
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class IntentType(str, Enum):
    """Types of user intents."""
    GREETING = "greeting"
    INFORMATIONAL = "informational"
    COMMAND_REQUEST = "command_request"
    COMMAND_HOW_TO = "command_how_to"
    WEB_SEARCH = "web_search"
    FILE_SEARCH = "file_search"
    SYSTEM_QUERY = "system_query"
    OCR_REQUEST = "ocr_request"
    IMAGE_GEN = "image_gen"
    CONVERSATION = "conversation"
    UNCLEAR = "unclear"


class IntentClassifier:
    """Classifies user intent using LLM and heuristics."""
    
    def __init__(self, message_bus=None):
        """Initialize the intent classifier."""
        self.message_bus = message_bus
        self._use_llm = True  # Can disable for testing
    
    async def classify(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify user intent.
        
        Args:
            user_input: The user's input text
            context: Optional context dict with keys like:
                - chat_mode: bool
                - prev_context: str
                - last_action: str
        
        Returns:
            {
                "intent": IntentType,
                "confidence": float (0.0-1.0),
                "parameters": dict,  # Extracted params
                "reasoning": str,
                "needs_approval": bool
            }
        """
        context = context or {}
        user_input = user_input.strip()
        
        # Quick heuristic checks for obvious cases (fast path)
        quick_result = self._quick_classify(user_input, context)
        if quick_result and quick_result.get("confidence", 0) >= 0.95:
            logger.info(
                "Intent classified (heuristic)",
                intent=quick_result["intent"],
                confidence=quick_result["confidence"]
            )
            return quick_result
        
        # Use LLM for ambiguous cases
        if self.message_bus and self._use_llm:
            try:
                llm_result = await self._llm_classify(user_input, context)
                if llm_result:
                    logger.info(
                        "Intent classified (LLM)",
                        intent=llm_result["intent"],
                        confidence=llm_result["confidence"]
                    )
                    return llm_result
            except Exception as e:
                logger.warning("LLM classification failed, using heuristic", error=str(e))
        
        # Fallback to heuristics
        result = quick_result or self._fallback_classify(user_input, context)
        logger.info(
            "Intent classified (fallback)",
            intent=result["intent"],
            confidence=result["confidence"]
        )
        return result
    
    def _quick_classify(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Quick heuristic classification for obvious cases."""
        lower = user_input.lower()
        
        # Slash commands (100% confidence)
        if lower.startswith("/"):
            return self._classify_slash_command(lower, context)
        
        # In chat mode, everything is conversation
        if context.get("chat_mode"):
            return {
                "intent": IntentType.CONVERSATION,
                "confidence": 0.98,
                "parameters": {},
                "reasoning": "In chat mode",
                "needs_approval": False
            }
        
        # Simple greetings (high confidence)
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", 
                     "good evening", "howdy", "greetings", "yo"]
        if any(lower.strip().rstrip("!.,") == g for g in greetings):
            return {
                "intent": IntentType.GREETING,
                "confidence": 0.99,
                "parameters": {},
                "reasoning": "Simple greeting match",
                "needs_approval": False
            }
        
        # Expanded greeting patterns
        greeting_patterns = ["how are you", "what's up", "how's it going",
                            "how are things", "how you doing"]
        if any(pattern in lower for pattern in greeting_patterns):
            return {
                "intent": IntentType.GREETING,
                "confidence": 0.95,
                "parameters": {},
                "reasoning": "Greeting pattern match",
                "needs_approval": False
            }
        
        # Web search (explicit keywords)
        web_keywords = ["search the web for", "search the web", "web search for",
                       "google for", "search online for", "look up online"]
        for kw in web_keywords:
            if kw in lower:
                query = lower.replace(kw, "").strip()
                return {
                    "intent": IntentType.WEB_SEARCH,
                    "confidence": 0.99,
                    "parameters": {"query": query},
                    "reasoning": f"Explicit web search keyword: {kw}",
                    "needs_approval": True  # To open browser
                }
        
        # System health queries
        health_patterns = ["system health", "check health", "health status",
                          "cpu usage", "memory usage", "disk space",
                          "system status", "resource usage"]
        if any(pattern in lower for pattern in health_patterns):
            return {
                "intent": IntentType.SYSTEM_QUERY,
                "confidence": 0.95,
                "parameters": {},
                "reasoning": "System health pattern",
                "needs_approval": False
            }
        
        # OCR requests
        ocr_patterns = ["ocr", "read text", "extract text", "recognize text"]
        if any(pattern in lower for pattern in ocr_patterns):
            return {
                "intent": IntentType.OCR_REQUEST,
                "confidence": 0.95,
                "parameters": {},
                "reasoning": "OCR pattern match",
                "needs_approval": False
            }
        
        # Image generation
        image_patterns = ["generate image", "create image", "make image",
                         "generate picture", "draw ", "paint "]
        if any(pattern in lower for pattern in image_patterns):
            return {
                "intent": IntentType.IMAGE_GEN,
                "confidence": 0.90,
                "parameters": {"prompt": user_input},
                "reasoning": "Image generation pattern",
                "needs_approval": False
            }
        
        # "How to" questions (wants instructions, not execution)
        how_to_patterns = ["how do i", "how to", "how can i", "how would i",
                          "show me how to", "teach me how to", "steps to"]
        if any(pattern in lower for pattern in how_to_patterns):
            # But check if it's really asking for execution
            action_follow = ["find", "list", "show", "get", "check"]
            has_action = any(f"{pattern} {action}" in lower 
                           for pattern in how_to_patterns 
                           for action in action_follow)
            
            return {
                "intent": IntentType.COMMAND_HOW_TO,
                "confidence": 0.85 if has_action else 0.75,
                "parameters": {},
                "reasoning": "How-to question pattern",
                "needs_approval": False
            }
        
        # Informational questions (question words + ?)
        question_starters = ["what is", "what's", "what are", "who is", "who's",
                            "why is", "why does", "when is", "where is",
                            "which is", "explain", "tell me about", "describe"]
        if any(lower.startswith(qs) for qs in question_starters) or lower.endswith("?"):
            # But not if it's asking to do something
            action_words = ["show me", "list", "find", "search", "get me"]
            if any(aw in lower for aw in action_words):
                return None  # Ambiguous, let LLM decide
            
            return {
                "intent": IntentType.INFORMATIONAL,
                "confidence": 0.85,
                "parameters": {},
                "reasoning": "Question pattern match",
                "needs_approval": False
            }
        
        # Command execution (mentions specific commands or utilities)
        # If the input mentions actual command names, it's almost certainly a command request
        command_names = [
            "tree", "ls", "ps", "top", "htop", "cat", "grep", "find", "locate",
            "du", "df", "free", "netstat", "ss", "ip", "ifconfig", "ping",
            "curl", "wget", "git", "docker", "systemctl", "journalctl",
            "apt", "yum", "dnf", "pacman", "npm", "pip", "chmod", "chown",
            "tar", "zip", "unzip", "sed", "awk", "sort", "head", "tail"
        ]
        # Use word boundaries to avoid false matches (e.g., "trees" shouldn't match "tree")
        for cmd in command_names:
            # Check if command appears as a word (not part of another word)
            if re.search(r'\b' + re.escape(cmd) + r'\b', lower):
                return {
                    "intent": IntentType.COMMAND_REQUEST,
                    "confidence": 0.95,  # High confidence - mentions specific command
                    "parameters": {},
                    "reasoning": f"Mentions command: {cmd}",
                    "needs_approval": True
                }
        
        # File search (searching INDEXED document content)
        file_search_patterns = ["find files", "search files", "locate files",
                               "files about", "files containing", "documents about",
                               "search documents", "find documents"]
        if any(pattern in lower for pattern in file_search_patterns):
            return {
                "intent": IntentType.FILE_SEARCH,
                "confidence": 0.90,
                "parameters": {"query": user_input},
                "reasoning": "File search pattern",
                "needs_approval": True  # To open file
            }
        
        # Imperative commands (high action verb density)
        # These are tricky - need to distinguish from "how to" questions
        strong_action_starts = ["show me", "list all", "find all", "get all",
                               "display", "run", "execute", "create",
                               "delete", "remove", "install", "update"]
        if any(lower.startswith(action) for action in strong_action_starts):
            return {
                "intent": IntentType.COMMAND_REQUEST,
                "confidence": 0.80,  # Slightly higher confidence
                "parameters": {},
                "reasoning": "Strong action verb at start",
                "needs_approval": True
            }
        
        # Not confident enough - return None to trigger LLM classification
        return None
    
    def _classify_slash_command(
        self,
        lower: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify slash commands."""
        if lower.startswith("/web "):
            query = lower[5:].strip()
            return {
                "intent": IntentType.WEB_SEARCH,
                "confidence": 1.0,
                "parameters": {"query": query},
                "reasoning": "Slash command /web",
                "needs_approval": True
            }
        elif lower.startswith("/search "):
            query = lower[8:].strip()
            return {
                "intent": IntentType.FILE_SEARCH,
                "confidence": 1.0,
                "parameters": {"query": query},
                "reasoning": "Slash command /search",
                "needs_approval": True
            }
        elif lower in ["/health", "/health summary"]:
            return {
                "intent": IntentType.SYSTEM_QUERY,
                "confidence": 1.0,
                "parameters": {},
                "reasoning": "Slash command /health",
                "needs_approval": False
            }
        elif lower in ["/ocr", "/ocr window"]:
            return {
                "intent": IntentType.OCR_REQUEST,
                "confidence": 1.0,
                "parameters": {},
                "reasoning": "Slash command /ocr",
                "needs_approval": False
            }
        else:
            # Unknown slash command
            return {
                "intent": IntentType.UNCLEAR,
                "confidence": 0.5,
                "parameters": {},
                "reasoning": "Unknown slash command",
                "needs_approval": False
            }
    
    async def _llm_classify(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to classify intent with structured output."""
        system_prompt = """You are an intent classifier for a Linux AI assistant.
Analyze the user's input and classify it into ONE of these intents:

IMPORTANT DISTINCTIONS:

1. **greeting**: Social pleasantries, greetings, casual conversation starters
   - "hello", "hi", "how are you", "good morning", "what's up"
   - Response: Friendly acknowledgment, NO command needed

2. **informational**: Questions seeking knowledge, explanations, or conceptual understanding
   - "what is docker?", "explain SSH", "why is the sky blue?"
   - "what does this command do?", "tell me about X"
   - Response: Educational explanation, NO command execution

3. **command_request**: User wants to EXECUTE a system command or action NOW
   - "show me large files", "list running processes", "create a directory"
   - "show me a tree of my home directory", "display running processes"
   - Mentions specific command names: tree, ls, ps, grep, docker, etc.
   - Key: User expects IMMEDIATE command execution/action
   - Response: Generate and execute command (with approval)

4. **command_how_to**: User asking HOW to do something (wants instructions)
   - "how do I find large files?", "how can I check disk space?"
   - "show me how to use grep", "what's the best way to X?"
   - Key: User wants to LEARN, not execute immediately
   - Response: Instructions and example commands to learn from

5. **web_search**: User wants to search the internet
   - "search web for X", "google Y", "look up Z online"

6. **file_search**: User wants to search INDEXED document CONTENT (semantic search)
   - "find documents about X", "search files containing Y", "documents about firewall"
   - Key: Searching THROUGH file content, not executing commands
   - Response: Search indexed files and show matches

7. **system_query**: User wants system status/health information
   - "check system health", "CPU usage", "memory status", "disk space"

8. **ocr_request**: User wants OCR/vision
   - "OCR window", "read text from screen", "extract text from image"

9. **image_gen**: User wants to generate an image
   - "generate image of X", "create picture of Y", "draw Z"

10. **conversation**: Continuing an ongoing conversation (when in chat mode)
    - Any input when chat mode is active
    - Follow-up questions or statements

CRITICAL: Distinguish between:
- "show me a tree of my home" → **command_request** (run tree command NOW)
- "find documents about firewall" → **file_search** (search indexed file content)
- "how do I list files" → **command_how_to** (wants instructions)
- "what is a directory" → **informational** (wants explanation)

Respond ONLY with valid JSON (no markdown, no backticks):
{{
    "intent": "<intent_type>",
    "confidence": 0.85,
    "parameters": {{
        "query": "extracted search query or command description if applicable"
    }},
    "reasoning": "Brief 1-sentence explanation of why you chose this intent"
}}

Current context:
- Chat mode active: {chat_mode}
- Last action: {last_action}

User input: {user_input}
"""

        prompt = system_prompt.format(
            chat_mode=context.get("chat_mode", False),
            last_action=context.get("last_action", "none"),
            user_input=user_input
        )
        
        try:
            response = await self.message_bus.request(
                "ai.llm.request",
                {
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input}
                    ],
                    "temperature": 0.1,  # Low temp for consistent classification
                    "max_tokens": 200
                },
                timeout=30.0  # Increased timeout for LLM classification
            )
            
            # Handle both dict and string responses
            if isinstance(response, dict):
                content = response.get("content", "").strip()
            else:
                content = str(response).strip()
            
            # Handle markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(line for line in lines if not line.strip().startswith("```"))
                content = content.strip()
            
            # Parse JSON - extract only the first JSON object if multiple are present
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                # Try to extract just the first JSON object
                try:
                    # Find the first complete JSON object
                    brace_count = 0
                    start_idx = content.find('{')
                    if start_idx == -1:
                        raise
                    
                    for i in range(start_idx, len(content)):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # Found complete JSON object
                                json_str = content[start_idx:i+1]
                                result = json.loads(json_str)
                                break
                    else:
                        raise
                except:
                    logger.warning("Failed to parse LLM intent JSON", content=content[:200], error=str(e))
                    return None
            
            # Validate intent type
            intent_str = result.get("intent", "").lower()
            try:
                intent = IntentType(intent_str)
            except ValueError:
                logger.warning(f"Unknown intent type from LLM: {intent_str}")
                return None
            
            # Add needs_approval based on intent type
            result["intent"] = intent
            result["needs_approval"] = intent in [
                IntentType.COMMAND_REQUEST,
                IntentType.WEB_SEARCH,
                IntentType.FILE_SEARCH
            ]
            
            # Ensure confidence is valid
            result["confidence"] = max(0.0, min(1.0, result.get("confidence", 0.7)))
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM intent JSON", error=str(e), content=content)
            return None
        except Exception as e:
            logger.error("LLM classification error", error=str(e))
            return None
    
    def _fallback_classify(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback classification when LLM and quick checks fail."""
        lower = user_input.lower()
        
        # Check for action words - if present, assume command request
        action_words = ["show", "list", "find", "search", "create", "delete",
                       "run", "execute", "check", "get", "display", "open"]
        has_action = any(word in lower.split() for word in action_words)
        
        # Check for question words - if present, assume informational
        question_words = ["what", "why", "how", "who", "when", "where", "which"]
        has_question = any(lower.startswith(word) for word in question_words) or lower.endswith("?")
        
        if has_question and not has_action:
            # Probably a question
            return {
                "intent": IntentType.INFORMATIONAL,
                "confidence": 0.6,
                "parameters": {},
                "reasoning": "Fallback: question words detected",
                "needs_approval": False
            }
        elif has_action:
            # Probably a command
            return {
                "intent": IntentType.COMMAND_REQUEST,
                "confidence": 0.5,
                "parameters": {},
                "reasoning": "Fallback: action words detected",
                "needs_approval": True
            }
        else:
            # Unclear, treat as conversation
            return {
                "intent": IntentType.CONVERSATION,
                "confidence": 0.4,
                "parameters": {},
                "reasoning": "Fallback: unclear intent",
                "needs_approval": False
            }

