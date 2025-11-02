"""Handlers for different intent types."""

from typing import Dict, Any, Optional
import structlog

from .intent import IntentType

logger = structlog.get_logger(__name__)


class IntentHandlers:
    """Handlers for different user intents."""
    
    def __init__(self, message_bus, context_getter=None):
        """
        Initialize intent handlers.
        
        Args:
            message_bus: NATS message bus client
            context_getter: Optional callable that returns current context dict
        """
        self.message_bus = message_bus
        self.context_getter = context_getter or (lambda: {})
    
    async def handle_greeting(self, user_input: str, params: Dict) -> Dict[str, Any]:
        """
        Handle greetings.
        
        Returns simple, friendly responses without LLM for common greetings.
        """
        # Simple greeting responses
        greetings_map = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What would you like to do?",
            "hey": "Hey! Ready to assist.",
            "good morning": "Good morning! How can I help?",
            "good afternoon": "Good afternoon! What can I do for you?",
            "good evening": "Good evening! How may I assist?",
            "howdy": "Howdy! What brings you here?",
            "yo": "Hey! What's up?",
        }
        
        lower = user_input.lower().strip().rstrip("!.,")
        
        if lower in greetings_map:
            return {
                "type": "text",
                "content": greetings_map[lower],
                "needs_approval": False
            }
        
        # For "how are you" type greetings
        if "how are" in lower or "how's it" in lower or "what's up" in lower:
            return {
                "type": "text",
                "content": "I'm running smoothly! Ready to help with your Linux tasks. What would you like to do?",
                "needs_approval": False
            }
        
        # Fallback to simple response
        return {
            "type": "text",
            "content": "Hello! I'm here to help. What can I do for you?",
            "needs_approval": False
        }
    
    async def handle_informational(self, user_input: str, params: Dict) -> Dict[str, Any]:
        """
        Handle informational/educational questions.
        
        Provides explanations without executing commands.
        """
        context = self.context_getter()
        context_str = self._format_context(context)
        
        system_prompt = """You are a helpful, knowledgeable Linux expert assistant.

Your role: Provide clear, accurate, educational answers to user questions.

Guidelines:
1. Explain concepts clearly and concisely
2. If relevant, mention related commands or tools (as examples, not to execute)
3. Provide context and background when helpful
4. If the question is about how to do something, give step-by-step guidance
5. Keep responses focused and practical
6. Use markdown formatting for readability

Important: The user is asking for INFORMATION, not requesting you execute anything.
If you mention commands, frame them as examples or suggestions for the user to try.

Current system context:
{context}
"""
        
        try:
            response = await self.message_bus.request(
                "ai.llm.request",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt.format(context=context_str)
                        },
                        {"role": "user", "content": user_input}
                    ],
                    "temperature": 0.4,
                    "max_tokens": 600
                },
                timeout=30.0
            )
            
            # Debug logging
            logger.debug("Informational handler response type", response_type=type(response).__name__, response=str(response)[:100])
            
            # Handle both dict and string responses
            if isinstance(response, dict):
                content = response.get("content", "").strip()
            else:
                content = str(response).strip()
            
            return {
                "type": "text",
                "content": content,
                "needs_approval": False
            }
            
        except Exception as e:
            logger.error("Error handling informational query", error=str(e))
            return {
                "type": "error",
                "content": f"I'm having trouble processing that question: {e}",
                "needs_approval": False
            }
    
    async def handle_command_request(self, user_input: str, params: Dict) -> Dict[str, Any]:
        """
        Handle command execution requests.
        
        Generates commands that need user approval before execution.
        """
        context = self.context_getter()
        context_str = self._format_context(context)
        
        system_prompt = """You are an expert Linux system administrator and shell scripting expert.
Your job is to convert natural language requests into safe, correct shell commands.

Rules:
1. Provide ONLY the command, no explanations
2. Use safe commands - avoid destructive operations without confirmation
3. Prefer standard Linux tools (bash, coreutils, etc.)
4. Consider the user's current context
5. If the request is ambiguous or potentially dangerous, provide the safest interpretation
6. For complex tasks, you may provide a pipeline or short script
7. Ensure commands are complete and executable

Current context:
{context}
"""
        
        try:
            response = await self.message_bus.request(
                "ai.llm.request",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt.format(context=context_str)
                        },
                        {"role": "user", "content": user_input}
                    ],
                    "temperature": 0.2,  # Low temp for consistent commands
                    "max_tokens": 400
                },
                timeout=30.0
            )
            
            # Handle both dict and string responses
            if isinstance(response, dict):
                content = response.get("content", "").strip()
            else:
                content = str(response).strip()
            
            # Clean up any markdown formatting
            if content.startswith("```"):
                lines = content.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                content = "\n".join(lines).strip()
            
            content = content.strip("`").strip()
            
            return {
                "type": "command_approval",
                "content": content,
                "explanation": f"Command for: {user_input}",
                "needs_approval": True,
                "pending_action": {
                    "type": "command",
                    "command": content
                }
            }
            
        except Exception as e:
            logger.error("Error generating command", error=str(e))
            return {
                "type": "error",
                "content": f"I couldn't generate a command for that: {e}",
                "needs_approval": False
            }
    
    async def handle_command_how_to(self, user_input: str, params: Dict) -> Dict[str, Any]:
        """
        Handle "how to" questions.
        
        Provides instructional responses with example commands.
        """
        context = self.context_getter()
        context_str = self._format_context(context)
        
        system_prompt = """You are a helpful Linux instructor and mentor.

The user is asking HOW to do something - they want to LEARN, not have you execute it.

Your response should:
1. Briefly explain what they're trying to achieve
2. Provide step-by-step instructions
3. Include example commands with explanations
4. Mention any important flags or options
5. Suggest alternative approaches if applicable
6. Warn about any risks or gotchas

Format:
- Use clear headings
- Show commands in code blocks with explanations
- Keep it practical and action-oriented
- Make it clear these are examples to learn from, not commands to execute now

Current context:
{context}
"""
        
        try:
            response = await self.message_bus.request(
                "ai.llm.request",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt.format(context=context_str)
                        },
                        {"role": "user", "content": user_input}
                    ],
                    "temperature": 0.5,
                    "max_tokens": 700
                },
                timeout=30.0
            )
            
            # Handle both dict and string responses
            if isinstance(response, dict):
                content = response.get("content", "").strip()
            else:
                content = str(response).strip()
            
            return {
                "type": "text",
                "content": content,
                "needs_approval": False
            }
            
        except Exception as e:
            logger.error("Error handling how-to question", error=str(e))
            return {
                "type": "error",
                "content": f"I couldn't provide instructions for that: {e}",
                "needs_approval": False
            }
    
    async def handle_conversation(self, user_input: str, params: Dict, history: list = None) -> Dict[str, Any]:
        """
        Handle conversational interactions.
        
        Uses chat mode with conversation history.
        """
        context = self.context_getter()
        
        messages = [
            {
                "role": "system",
                "content": "You are Neuralux, a helpful AI assistant for Linux. Provide natural, concise responses. Be friendly and helpful."
            }
        ]
        
        # Add conversation history
        if history:
            for msg in history[-10:]:  # Last 10 messages
                messages.append(msg)
        
        # Add current input
        messages.append({"role": "user", "content": user_input})
        
        try:
            response = await self.message_bus.request(
                "ai.llm.request",
                {
                    "messages": messages,
                    "temperature": 0.6,
                    "max_tokens": 500
                },
                timeout=30.0
            )
            
            # Handle both dict and string responses
            if isinstance(response, dict):
                content = response.get("content", "").strip()
            else:
                content = str(response).strip()
            
            return {
                "type": "text",
                "content": content,
                "needs_approval": False
            }
            
        except Exception as e:
            logger.error("Error in conversation", error=str(e))
            return {
                "type": "error",
                "content": f"Sorry, I'm having trouble responding: {e}",
                "needs_approval": False
            }
    
    async def handle_image_generation(self, user_input: str, params: Dict) -> Dict[str, Any]:
        """
        Handle image generation requests.
        
        Extracts or refines the prompt and returns image gen request.
        """
        prompt = params.get("prompt", user_input)
        
        # If prompt is the full input like "generate image of sunset", clean it up
        lower_prompt = prompt.lower()
        prefixes = ["generate image of ", "generate image ", "create image of ", "create image ",
                    "make image of ", "make image ", "generate picture of ", "generate picture ",
                    "create picture of ", "create picture ", "draw ", "paint ", "generate "]
        
        for prefix in prefixes:
            if lower_prompt.startswith(prefix):
                prompt = prompt[len(prefix):].strip()
                break
        
        return {
            "type": "image_generation",
            "content": prompt,
            "prompt": prompt,
            "needs_approval": False
        }

    async def handle_music_generation(self, user_input: str, params: Dict) -> Dict[str, Any]:
        """
        Handle music generation requests.
        
        Extracts or refines the prompt and returns music gen request.
        """
        prompt = params.get("prompt", user_input)
        
        # If prompt is the full input like "generate song about...", clean it up
        lower_prompt = prompt.lower()
        prefixes = [
            "generate song about ", "generate song ", "create song about ", "create song ",
            "make song about ", "make song ", "generate music about ", "generate music ",
            "create music about ", "create music ", "compose song about ", "compose song ",
            "compose music about ", "compose music "
        ]
        
        for prefix in prefixes:
            if lower_prompt.startswith(prefix):
                prompt = prompt[len(prefix):].strip()
                break
        
        return {
            "type": "music_generation",
            "content": prompt,
            "prompt": prompt,
            "needs_approval": False
        }
    
    async def handle_system_command(self, user_input: str, params: Dict) -> Dict[str, Any]:
        """
        Handle system command requests.
        
        Generates system actions that need user approval before execution.
        """
        # Simple parsing for now, can be improved with LLM later
        lower_input = user_input.lower()
        action = None
        
        if "list" in lower_input and "process" in lower_input:
            action = "process.list"
            payload = {}
        elif ("kill" in lower_input or "terminate" in lower_input) and "process" in lower_input:
            action = "process.kill"
            # Extract PID, simple regex for now
            import re
            match = re.search(r'\d+', user_input)
            if match:
                pid = int(match.group(0))
                payload = {"pid": pid}
            else:
                return {
                    "type": "error",
                    "content": "Could not find a PID to kill in your request.",
                    "needs_approval": False
                }
        else:
            return {
                "type": "error",
                "content": "Sorry, I don't understand that system command.",
                "needs_approval": False
            }

        return {
            "type": "system_command_approval",
            "content": f"Request to {action} with parameters {payload}",
            "explanation": f"System command for: {user_input}",
            "needs_approval": True,
            "pending_action": {
                "type": "system_command",
                "action": action,
                "payload": payload
            }
        }

    def _format_context(self, context: Any) -> str:
        """Format context into a string for prompts."""
        # Handle case where context_getter returns a string
        if isinstance(context, str):
            return context if context else "No additional context available"
        
        # Handle dict context
        if not context or not isinstance(context, dict):
            return "No additional context available"
        
        parts = []
        
        if context.get("cwd"):
            parts.append(f"Current directory: {context['cwd']}")
        
        if context.get("active_app"):
            parts.append(f"Active application: {context['active_app']}")
        
        if context.get("git_branch"):
            parts.append(f"Git branch: {context['git_branch']}")
        
        if context.get("last_command"):
            parts.append(f"Last command: {context['last_command']}")
        
        return "\n".join(parts) if parts else "No additional context available"


class IntentRouter:
    """Routes intents to appropriate handlers."""
    
    def __init__(self, handlers: IntentHandlers):
        """Initialize the router with handlers."""
        self.handlers = handlers
    
    async def route(
        self,
        intent_result: Dict[str, Any],
        user_input: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Route intent to appropriate handler.
        
        Args:
            intent_result: Result from IntentClassifier.classify()
            user_input: Original user input
            **kwargs: Additional args for specific handlers (e.g., history)
        
        Returns:
            Handler result dict with type, content, needs_approval, etc.
        """
        intent = intent_result.get("intent")
        params = intent_result.get("parameters", {})
        
        logger.info("Routing intent", intent=intent)
        
        try:
            if intent == IntentType.GREETING:
                result = await self.handlers.handle_greeting(user_input, params)
            
            elif intent == IntentType.INFORMATIONAL:
                result = await self.handlers.handle_informational(user_input, params)
            
            elif intent == IntentType.COMMAND_REQUEST:
                result = await self.handlers.handle_command_request(user_input, params)
            
            elif intent == IntentType.COMMAND_HOW_TO:
                result = await self.handlers.handle_command_how_to(user_input, params)
            
            elif intent == IntentType.CONVERSATION:
                history = kwargs.get("history", [])
                result = await self.handlers.handle_conversation(user_input, params, history)
            
            elif intent == IntentType.IMAGE_GEN:
                result = await self.handlers.handle_image_generation(user_input, params)

            elif intent == IntentType.MUSIC_GEN:
                result = await self.handlers.handle_music_generation(user_input, params)
            
            elif intent == IntentType.SYSTEM_COMMAND:
                result = await self.handlers.handle_system_command(user_input, params)

            else:
                # For other types (web_search, file_search, etc.), return info for caller to handle
                # since they need access to specific services
                result = {
                    "type": "needs_external_handler",
                    "intent": intent,
                    "parameters": params,
                    "needs_approval": intent_result.get("needs_approval", False)
                }
            
            # Debug: Check result type
            logger.debug("Handler result type", result_type=type(result).__name__, has_get=hasattr(result, 'get'))
            return result
        
        except Exception as e:
            import traceback
            logger.error("Error routing intent", intent=intent, error=str(e), traceback=traceback.format_exc())
            return {
                "type": "error",
                "content": f"I encountered an error processing that: {e}",
                "needs_approval": False
            }
