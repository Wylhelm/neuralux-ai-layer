"""Context-aware action planner for multi-step conversational workflows."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
import structlog

from .conversation import ConversationContext, ReferenceResolver, ActionType
from .orchestrator import Action, ActionStatus
from .messaging import MessageBusClient

logger = structlog.get_logger(__name__)


class ActionPlanner:
    """Plans actions based on user input and conversation context."""
    
    def __init__(self, message_bus: MessageBusClient):
        """Initialize action planner."""
        self.message_bus = message_bus
    
    async def plan_actions(
        self,
        user_input: str,
        context: ConversationContext,
    ) -> Tuple[List[Action], str]:
        """
        Plan actions based on user input and context.
        
        Args:
            user_input: User's request
            context: Conversation context
            
        Returns:
            (list_of_actions, explanation)
        """
        logger.info("planning_actions", input=user_input, session=context.session_id)
        
        # Let the LLM handle conversational inputs - it's more intelligent than patterns!
        
        # Check for simple reference patterns BEFORE LLM (to avoid misinterpretation)
        # These are common cases where users reference previous results by number
        quick_actions, quick_explanation = self._try_quick_reference_patterns(user_input, context)
        if quick_actions:
            return quick_actions, quick_explanation
        
        # Fast-path: informational Q&A and conversational inputs bypass planner LLM
        lower_input_for_intent = user_input.lower()
        if self._is_informational_query(lower_input_for_intent):
            params = {
                "prompt": user_input,
                "use_history": True,
                "system_prompt": (
                    "You are Neuralux, a friendly and helpful AI assistant. "
                    "Respond naturally and conversationally. "
                    "For greetings, be warm and welcoming. "
                    "For questions, answer directly, accurately, and concisely. "
                    "Be personable and helpful. Keep responses brief but complete."
                ),
                "temperature": 0.7,  # More natural for conversation
                "max_tokens": 300,
            }
            return [Action(
                action_type=ActionType.LLM_GENERATE,
                params=params,
                description="Respond to user",
                needs_approval=False,
            )], "Responding to your message"
        
        # Check if input needs reference resolution
        if ReferenceResolver.needs_resolution(user_input):
            resolved_input, resolved_values = ReferenceResolver.resolve(user_input, context)
            logger.debug("resolved_references", resolved_values=resolved_values)
        else:
            resolved_input = user_input
            resolved_values = {}
        
        # Use LLM to plan actions
        actions, explanation = await self._llm_plan_actions(
            user_input,
            resolved_input,
            resolved_values,
            context,
        )
        
        # Post-process actions (add resolved values)
        for action in actions:
            self._enrich_action_params(action, resolved_values, context)
        
        logger.info("planned_actions", count=len(actions), explanation=explanation)
        return actions, explanation
    
    def _try_quick_reference_patterns(
        self,
        user_input: str,
        context: ConversationContext,
    ) -> Tuple[List[Action], str]:
        """
        Check for simple reference patterns that should bypass LLM planning.
        This prevents the LLM from misinterpreting things like "open document 10" as a search query.
        
        Returns:
            (list_of_actions, explanation) or ([], "") if no pattern matched
        """
        lower_input = user_input.lower().strip()
        
        # Pattern 1: Open link from web search results
        # "open link 1", "visit site 2", "go to url 3"
        if ("link" in lower_input or "site" in lower_input or "url" in lower_input):
            link_match = re.search(r"(?:link|site|url|result)\s+(\d+)", lower_input)
            if link_match:
                link_num = int(link_match.group(1))
                search_results = context.get_variable("last_search_results", [])
                if search_results and 1 <= link_num <= len(search_results):
                    url = search_results[link_num - 1].get("url", "")
                    if url:
                        return [Action(
                            action_type=ActionType.COMMAND_EXECUTE,
                            params={"command": f"xdg-open '{url}'"},
                            description=f"Execute: xdg-open '{url}'",
                            needs_approval=True,
                        )], f"Opening link #{link_num}"
        
        # Pattern 2: Open document from query results
        # "open 1", "show 2", "read 3", "open document 10", etc.
        # Look for any number that could be a document reference
        if "open" in lower_input or "show" in lower_input or "read" in lower_input:
            # Match various patterns
            doc_match = re.search(r"(?:open|show|read|document|doc)\s+(?:document\s+|doc\s+)?(\d+)", lower_input)
            if doc_match:
                doc_num = int(doc_match.group(1))
                query_results = context.get_variable("last_query_results", [])
                if query_results and 1 <= doc_num <= len(query_results):
                    doc_path = query_results[doc_num - 1].get("file_path") or query_results[doc_num - 1].get("path", "")
                    if doc_path:
                        # Use xdg-open to open documents in their default application
                        # (LibreOffice for .odt, text editor for .txt, etc.)
                        return [Action(
                            action_type=ActionType.COMMAND_EXECUTE,
                            params={"command": f"xdg-open '{doc_path}'"},
                            description=f"Execute: xdg-open '{doc_path}'",
                            needs_approval=True,
                        )], f"Opening document #{doc_num}"
        
        # No quick pattern matched
        return [], ""
    
    async def _llm_plan_actions(
        self,
        original_input: str,
        resolved_input: str,
        resolved_values: Dict[str, Any],
        context: ConversationContext,
    ) -> Tuple[List[Action], str]:
        """Use LLM to plan actions from user input."""
        
        # Build system prompt with available actions
        system_prompt = self._build_action_planning_prompt(context, resolved_values)
        
        # Build user message
        user_message = f"""User request: {original_input}

Plan the required actions to fulfill this request. Respond in JSON format with:
{{
  "explanation": "Brief explanation of what you'll do",
  "actions": [
    {{
      "action_type": "file_create|file_write|image_generate|image_save|llm_generate|ocr_capture",
      "params": {{}},
      "description": "What this action does",
      "needs_approval": true/false
    }}
  ]
}}"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            
            response = await self.message_bus.request(
                "ai.llm.request",
                {
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 300,  # Further reduced for faster planning
                },
                timeout=20.0,
            )
            
            content = response.get("content", "")
            
            # Parse JSON response
            import json
            
            # Try to extract JSON from the response
            json_str = content.strip()
            
            # 1. First try markdown code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            # 2. If starts with {, extract until the matching }
            elif json_str.startswith('{'):
                brace_count = 0
                end_pos = 0
                for i, char in enumerate(json_str):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                if end_pos > 0:
                    json_str = json_str[:end_pos]
            
            plan = json.loads(json_str)
            
            explanation = plan.get("explanation", "Processing your request")
            actions_data = plan.get("actions", [])
            
            actions = []
            for action_data in actions_data:
                try:
                    action_type = ActionType(action_data.get("action_type", "llm_generate"))
                    params = action_data.get("params", {})
                    description = action_data.get("description", "")
                    needs_approval = action_data.get("needs_approval", True)
                    
                    action = Action(
                        action_type=action_type,
                        params=params,
                        description=description,
                        needs_approval=needs_approval,
                    )
                    actions.append(action)
                except Exception as e:
                    logger.error("failed_to_parse_action", error=str(e), data=action_data)
            
            return actions, explanation
            
        except Exception as e:
            logger.error("llm_action_planning_failed", error=str(e))
            
            # Fallback to pattern-based planning
            return self._fallback_plan_actions(original_input, resolved_values, context)
    
    def _build_action_planning_prompt(
        self,
        context: ConversationContext,
        resolved_values: Dict[str, Any],
    ) -> str:
        """Build system prompt for action planning."""
        
        # Get context summary
        variables_summary = []
        for key, value in context.variables.items():
            if isinstance(value, str):
                variables_summary.append(f"- {key}: {value[:100]}")
            else:
                variables_summary.append(f"- {key}: {type(value).__name__}")
        
        resolved_summary = []
        for key, value in resolved_values.items():
            resolved_summary.append(f"- {key}: {value}")
        
        prompt = f"""You are an AI action planner for a command-line assistant. Your job is to break down user requests into executable actions.

This is a HYBRID system:
- AI capabilities (llm, image generation, OCR, document search) have dedicated actions
- File/system operations use shell commands (command_execute)

Available action types:

AI-SPECIFIC ACTIONS (not shell commands):
1. llm_generate - Generate text with AI
   params: prompt (str), system_prompt (str, optional), temperature (float, default 0.7), max_tokens (int, default 500), use_history (bool, default false)
   needs_approval: false

2. image_generate - Generate an image with AI
   params: prompt (str), width (int, default 1024), height (int, default 1024), steps (int, default 4)
   needs_approval: false
   
3. image_save - Save AI-generated image to a specific location
   params: src_path (str), dst_path (str)
   needs_approval: true
   
4. ocr_capture - Extract text from image/screen with OCR
   params: image_path (str, optional), region (str, optional), language (str, optional)
   needs_approval: false

5. document_query - Search indexed documents (RAG/semantic search)
   params: query (str), limit (int, default 10)
   needs_approval: false

6. web_search - Search the web using DuckDuckGo
   params: query (str), limit (int, default 5)
   needs_approval: false
   
COMMAND EXECUTION (for file/system operations):
7. command_execute - Execute ANY shell command
   params: command (str)
   needs_approval: true (ALWAYS)
   
   Common commands:
   - Create file: touch filename OR echo "content" > filename
   - Write to file: echo "content" > filename (overwrite) OR echo "content" >> filename (append)
   - Read text file: cat filename (for .txt, .log, etc.)
   - Open document: xdg-open filename (for .odt, .pdf, .doc, images, etc.)
   - Move file: mv source destination
   - Delete file: rm filename
   - Create directory: mkdir -p dirname
   - List files: ls -la [path]
   - Any other shell command the user wants

Current context:
Working directory: {context.working_directory or "~"}

Context variables:
{chr(10).join(variables_summary) if variables_summary else "- None"}

Resolved references:
{chr(10).join(resolved_summary) if resolved_summary else "- None"}

Path shortcuts you can use:
- Use "~/Pictures", "~/Documents", "~/Downloads", "~/Desktop" etc.
- Use "Pictures" or "pictures" folder instead of full path
- Paths will be automatically expanded

Important rules:
1. ALL command_execute actions ALWAYS require approval - user must see exact command
2. AI actions (llm_generate, image_generate, ocr_capture, document_query) don't need approval
3. When generating content for a file: llm_generate first, then command_execute with echo
4. Use proper shell quoting for content with special characters
5. Chain actions: one action's output feeds into the next
6. For image operations: use image_save (not command_execute) to save generated images

Examples:

User: "create a file named test.txt"
Response: {{"explanation": "Creating file", "actions": [{{"action_type": "command_execute", "params": {{"command": "touch test.txt"}}, "description": "Execute: touch test.txt", "needs_approval": true}}]}}

User: "create notes.txt with hello world in it"
Response: {{"explanation": "Creating file with content", "actions": [{{"action_type": "command_execute", "params": {{"command": "echo 'hello world' > notes.txt"}}, "description": "Execute: echo 'hello world' > notes.txt", "needs_approval": true}}]}}

User: "write a summary of Marie Curie in summary.txt"
Response: {{"explanation": "Generate and write summary", "actions": [
  {{"action_type": "llm_generate", "params": {{"prompt": "Write a concise summary of Marie Curie's life"}}, "description": "Generate Marie Curie summary", "needs_approval": false}},
  {{"action_type": "command_execute", "params": {{"command": "cat > summary.txt"}}, "description": "Execute: cat > summary.txt (with generated content)", "needs_approval": true}}
]}}

User: "read that file"  (after file operation)
Response: {{"explanation": "Reading file", "actions": [{{"action_type": "command_execute", "params": {{"command": "cat summary.txt"}}, "description": "Execute: cat summary.txt", "needs_approval": true}}]}}

User: "search my documents for Python tutorials"
Response: {{"explanation": "Searching indexed documents", "actions": [{{"action_type": "document_query", "params": {{"query": "Python tutorials", "limit": 10}}, "description": "Search: Python tutorials", "needs_approval": false}}]}}

User: "open document 3" or "show me doc 2" (after a search)
Response: {{"explanation": "Opening document", "actions": [{{"action_type": "command_execute", "params": {{"command": "xdg-open /path/to/document"}}, "description": "Execute: xdg-open /path/to/document", "needs_approval": true}}]}}

User: "search the web for Python 3.12 new features"
Response: {{"explanation": "Searching web", "actions": [{{"action_type": "web_search", "params": {{"query": "Python 3.12 new features", "limit": 5}}, "description": "Search web: Python 3.12", "needs_approval": false}}]}}

User: "open link 2" or "visit site 1" (after a web search)
Response: {{"explanation": "Opening link", "actions": [{{"action_type": "command_execute", "params": {{"command": "xdg-open 'https://example.com'"}}, "description": "Execute: xdg-open...", "needs_approval": true}}]}}

User: "generate an image of a sunset"
Response: {{"explanation": "Generating image", "actions": [{{"action_type": "image_generate", "params": {{"prompt": "beautiful sunset over ocean"}}, "description": "Generate sunset image", "needs_approval": false}}]}}

User: "save it to Pictures"  (after generating image)
Response: {{"explanation": "Saving image", "actions": [{{"action_type": "image_save", "params": {{"src_path": "{{last_generated_image}}", "dst_path": "~/Pictures"}}, "description": "Save to Pictures folder", "needs_approval": true}}]}}

User: "show my docker containers"
Response: {{"explanation": "Listing containers", "actions": [{{"action_type": "command_execute", "params": {{"command": "docker ps -a"}}, "description": "Execute: docker ps -a", "needs_approval": true}}]}}

User: "list my files"
Response: {{"explanation": "Listing files", "actions": [{{"action_type": "command_execute", "params": {{"command": "ls -la ~"}}, "description": "Execute: ls -la ~", "needs_approval": true}}]}}

User: "create a folder named test"
Response: {{"explanation": "Creating directory", "actions": [{{"action_type": "command_execute", "params": {{"command": "mkdir -p ~/test"}}, "description": "Execute: mkdir -p ~/test", "needs_approval": true}}]}}

Now plan the actions for the user's request."""
        
        return prompt

    def _is_informational_query(self, lower_input: str) -> bool:
        """Heuristic to detect pure informational Q&A and conversational inputs.
        
        This catches questions, greetings, and non-imperative conversational requests.
        """
        # Question mark is a strong indicator
        if "?" in lower_input:
            return True
        
        # Greetings and conversational phrases (let LLM handle naturally)
        conversational_words = (
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "thanks", "thank you", "bye", "goodbye", "how are you", "what's up",
            "greetings", "howdy", "bonjour", "hola", "ciao", "salut",
        )
        if any(phrase in lower_input for phrase in conversational_words):
            return True
        
        # Common interrogatives and informational verbs
        starters = (
            "what", "who", "when", "where", "why", "how",
            "explain", "tell me", "summarize", "summary of",
            "define", "describe", "compare", "difference between",
            "translate", "meaning of", "calculate", "compute",
            "can you", "could you", "would you", "please",
        )
        if any(lower_input.startswith(s) for s in starters):
            return True
        
        # Avoid matching obvious imperative system intents
        imperative_keywords = (
            "open", "create", "write", "save", "move", "delete",
            "list files", "search files", "run", "execute", "install",
            "generate image", "ocr", "web search",
        )
        if any(k in lower_input for k in imperative_keywords):
            return False
        
        # Short, declarative informational prompts
        if len(lower_input.split()) >= 3 and any(w in lower_input for w in ("info", "information", "overview", "guide")):
            return True
        
        return False
    
    def _fallback_plan_actions(
        self,
        user_input: str,
        resolved_values: Dict[str, Any],
        context: ConversationContext,
    ) -> Tuple[List[Action], str]:
        """Fallback pattern-based action planning when LLM fails."""
        
        logger.info("using_fallback_action_planning")
        
        actions = []
        explanation = "Processing your request"
        
        lower_input = user_input.lower()
        
        # Pattern: Create file (stronger detection, before folder detection)
        if "create" in lower_input and "file" in lower_input:
            filename = None
            # 1) "create a NAME file" or "create NAME file"
            m1 = re.search(r"create\s+(?:a\s+|an\s+)?([^\s]+)\s+file", lower_input)
            # 2) "create a file named NAME" / "create file called NAME"
            m2 = re.search(r"create\s+(?:a\s+)?file\s+(?:named|called)\s+([^\s]+)", lower_input)
            # 3) "create file NAME"
            m3 = re.search(r"create\s+file\s+([^\s]+)", lower_input)
            # 4) fallback to previous "named NAME"
            m4 = re.search(r"named?\s+([^\s]+)", lower_input)
            for m in (m1, m2, m3, m4):
                if m:
                    filename = m.group(1)
                    break
            if filename:
                # If it mistakenly looks like a directory intent with trailing '/', normalize
                filename = filename.rstrip('/')
                command = f"touch {filename}"
                actions.append(Action(
                    action_type=ActionType.COMMAND_EXECUTE,
                    params={"command": command},
                    description=f"Execute: {command}",
                    needs_approval=True,
                ))
                explanation = f"Creating file {filename}"
        
        # Pattern: Create folder/directory (after file detection to avoid misclassification)
        elif "create" in lower_input and ("folder" in lower_input or "directory" in lower_input or "dir" in lower_input):
            # Extract folder name
            match = re.search(r"named?\s+([^\s]+)", lower_input)
            if match:
                foldername = match.group(1)
                # Expand to full path
                if not foldername.startswith('/') and not foldername.startswith('~'):
                    foldername = f"~/{foldername}"
                
                command = f"mkdir -p {foldername}"
                actions.append(Action(
                    action_type=ActionType.COMMAND_EXECUTE,
                    params={"command": command},
                    description=f"Execute: {command}",
                    needs_approval=True,
                ))
                explanation = f"Creating directory {foldername}"
        
        # Pattern: Write to file
        elif "write" in lower_input and ("to" in lower_input or "in" in lower_input):
            # Check if we need to generate content first
            if "summary" in lower_input or "about" in lower_input:
                # Extract topic
                topic = "the requested topic"
                if "of" in lower_input:
                    topic_match = re.search(r"of\s+(.+?)(?:\s+to|\s+in|$)", lower_input)
                    if topic_match:
                        topic = topic_match.group(1).strip()
                
                actions.append(Action(
                    action_type=ActionType.LLM_GENERATE,
                    params={"prompt": f"Write a concise summary about {topic}"},
                    description=f"Generate summary about {topic}",
                    needs_approval=False,
                ))
            
            # Determine target file; handle pronoun "in it" by using last_created_file, and detect explicit filenames with extensions
            file_path = resolved_values.get("file_path") or context.get_variable("last_created_file", "output.txt")
            # If an explicit filename is present after "in" or "to", prefer it
            explicit = None
            m = re.search(r"(?:in|to)\s+([^\s]+)\b", lower_input)
            if m:
                candidate = m.group(1).rstrip('/')
                # Treat as a file if it has an extension
                if "." in candidate and not candidate.endswith('.'):
                    explicit = candidate
            if explicit:
                file_path = explicit
            
            # Use cat > to write generated content
            command = f"cat > {file_path}"
            actions.append(Action(
                action_type=ActionType.COMMAND_EXECUTE,
                params={"command": command},
                description=f"Execute: {command} (with generated content)",
                needs_approval=True,
            ))
            explanation = f"Writing content to {file_path}"
        
        # Pattern: Generate image
        elif "generate" in lower_input and "image" in lower_input:
            # Extract prompt (everything after "of" or "image")
            prompt_match = re.search(r"image\s+(?:of\s+)?(.+?)(?:\s+and|\s+then|$)", lower_input)
            if prompt_match:
                prompt = prompt_match.group(1).strip()
            else:
                prompt = "a beautiful scene"
            
            actions.append(Action(
                action_type=ActionType.IMAGE_GENERATE,
                params={"prompt": prompt},
                description=f"Generate image: {prompt}",
                needs_approval=False,
            ))
            explanation = f"Generating image: {prompt}"
        
        # Pattern: Save image
        elif "save" in lower_input and ("image" in lower_input or "it" in lower_input):
            # Extract destination
            dest_match = re.search(r"to\s+(?:my\s+)?(.+?)(?:\s+folder|$)", lower_input)
            if dest_match:
                destination = dest_match.group(1).strip()
            else:
                destination = "~/Pictures"
            
            src_path = resolved_values.get("image_path") or context.get_variable("last_generated_image", "")
            
            if src_path:
                actions.append(Action(
                    action_type=ActionType.IMAGE_SAVE,
                    params={"src_path": src_path, "dst_path": destination},
                    description=f"Save image to {destination}",
                    needs_approval=True,
                ))
                explanation = f"Saving image to {destination}"
        
        # Pattern: List files
        elif "list" in lower_input and ("file" in lower_input or "folder" in lower_input or "director" in lower_input):
            # Determine path
            path = "~"
            if "home" in lower_input or "~" in lower_input:
                path = "~"
            elif "current" in lower_input or "here" in lower_input:
                path = "."
            
            command = f"ls -la {path}"
            actions.append(Action(
                action_type=ActionType.COMMAND_EXECUTE,
                params={"command": command},
                description=f"Execute: {command}",
                needs_approval=True,
            ))
            explanation = f"Listing files in {path}"
        
        # Pattern: Document search
        elif "search" in lower_input and ("document" in lower_input or "file" in lower_input or "my" in lower_input):
            # Extract search query
            query_match = re.search(r"(?:search|find)(?:\s+my)?(?:\s+documents?)?(?:\s+for)?\s+(.+)", lower_input)
            if query_match:
                query = query_match.group(1).strip()
                actions.append(Action(
                    action_type=ActionType.DOCUMENT_QUERY,
                    params={"query": query, "limit": 10},
                    description=f"Search: {query}",
                    needs_approval=False,
                ))
                explanation = f"Searching documents for: {query}"
        
        # Pattern: Read file
        elif "read" in lower_input or "cat" in lower_input or "show" in lower_input:
            # Try to extract filename
            filename_match = re.search(r"(?:read|cat|show)\s+(.+?)(?:\s+file)?$", lower_input)
            if filename_match:
                filename = filename_match.group(1).strip()
                command = f"cat {filename}"
                actions.append(Action(
                    action_type=ActionType.COMMAND_EXECUTE,
                    params={"command": command},
                    description=f"Execute: {command}",
                    needs_approval=True,
                ))
                explanation = f"Reading file {filename}"
        
        # Pattern: Web search
        elif "search" in lower_input and ("web" in lower_input or "google" in lower_input or "duckduckgo" in lower_input or "internet" in lower_input):
            # Extract search query
            query_match = re.search(r"(?:search|google|find)(?:\s+(?:for|the|web|internet))?\s+(.+)", lower_input, re.IGNORECASE)
            if query_match:
                query = query_match.group(1).strip()
                actions.append(Action(
                    action_type=ActionType.WEB_SEARCH,
                    params={"query": query, "limit": 5},
                    description=f"Search web: {query}",
                    needs_approval=False,
                ))
                explanation = f"Searching web for: {query}"
        
        # Pattern: Open link from search results (check this first - more specific)
        elif ("open" in lower_input or "visit" in lower_input or "go to" in lower_input) and ("link" in lower_input or "site" in lower_input or "url" in lower_input):
            # Extract link number
            link_match = re.search(r"(?:link|site|url|result)\s+(\d+)", lower_input)
            if link_match:
                link_num = int(link_match.group(1))
                # Get the link from last search results
                search_results = context.get_variable("last_search_results", [])
                if search_results and 1 <= link_num <= len(search_results):
                    url = search_results[link_num - 1].get("url", "")
                    if url:
                        command = f"xdg-open '{url}'"
                        actions.append(Action(
                            action_type=ActionType.COMMAND_EXECUTE,
                            params={"command": command},
                            description=f"Execute: {command}",
                            needs_approval=True,
                        ))
                        explanation = f"Opening link #{link_num}"
        
        # Pattern: Open document from query results
        # Matches: "open 1", "open document 1", "show doc 2", "read 3", etc.
        elif "open" in lower_input or "show" in lower_input or "read" in lower_input:
            # Try to extract a number that might refer to a document
            doc_match = re.search(r"(?:open|show|read|document|doc)\s+(\d+)", lower_input)
            if doc_match:
                doc_num = int(doc_match.group(1))
                # Get the document from last query results
                query_results = context.get_variable("last_query_results", [])
                if query_results and 1 <= doc_num <= len(query_results):
                    # Handle both 'path' and 'file_path' field names
                    doc_path = query_results[doc_num - 1].get("file_path") or query_results[doc_num - 1].get("path", "")
                    if doc_path:
                        # Use xdg-open to open documents in their default application
                        command = f"xdg-open '{doc_path}'"
                        actions.append(Action(
                            action_type=ActionType.COMMAND_EXECUTE,
                            params={"command": command},
                            description=f"Execute: {command}",
                            needs_approval=True,
                        ))
                        explanation = f"Opening document #{doc_num}"
        
        # Pattern: OCR
        elif "ocr" in lower_input or "extract text" in lower_input:
            params = {}
            if "window" in lower_input:
                params["window"] = True
            elif "region" in lower_input:
                # Try to extract region, e.g., "from region 100,100,200,50"
                match = re.search(r"region\s+([\d,]+)", lower_input)
                if match:
                    params["region"] = match.group(1)
            
            actions.append(Action(
                action_type=ActionType.OCR_CAPTURE,
                params=params,
                description="Capture text from screen",
                needs_approval=False,
            ))
            explanation = "Capturing text via OCR"
        
        # Default: Ask LLM for help
        if not actions:
            actions.append(Action(
                action_type=ActionType.LLM_GENERATE,
                params={"prompt": user_input, "use_history": True},
                description="Process request",
                needs_approval=False,
            ))
            explanation = "Processing your request"
        
        return actions, explanation
    
    def _enrich_action_params(
        self,
        action: Action,
        resolved_values: Dict[str, Any],
        context: ConversationContext,
    ):
        """Enrich action parameters with resolved values and context."""
        
        # Replace placeholders in params
        for key, value in action.params.items():
            if isinstance(value, str):
                # Replace context variable placeholders
                if "{{last_created_file}}" in value:
                    last_file = context.get_variable("last_created_file", "")
                    value = value.replace("{{last_created_file}}", last_file)
                
                if "{{last_generated_image}}" in value:
                    last_image = context.get_variable("last_generated_image", "")
                    value = value.replace("{{last_generated_image}}", last_image)
                
                if "{{last_ocr_text}}" in value:
                    last_ocr = context.get_variable("last_ocr_text", "")
                    value = value.replace("{{last_ocr_text}}", last_ocr)
                
                # Note: {{llm_output}} will be handled during execution
                
                action.params[key] = value
        
        # Add resolved values if not already in params
        if action.action_type == ActionType.IMAGE_SAVE:
            if "src_path" not in action.params and "image_path" in resolved_values:
                action.params["src_path"] = resolved_values["image_path"]
