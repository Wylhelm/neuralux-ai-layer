# Intent System Integration Guide

This guide shows how to integrate the new intent classification system into the existing codebase.

## Overview

The intent system consists of:
1. **IntentClassifier** (`neuralux/intent.py`) - Classifies user intent
2. **IntentHandlers** (`neuralux/intent_handlers.py`) - Handles each intent type
3. **IntentRouter** - Routes intents to appropriate handlers

## Integration Steps

### Step 1: Update AIShell Class

Add the intent system to the `AIShell` class in `packages/cli/aish/main.py`:

```python
# Add imports at the top
from neuralux.intent import IntentClassifier, IntentType
from neuralux.intent_handlers import IntentHandlers, IntentRouter

class AIShell:
    """AI-powered shell assistant."""
    
    def __init__(self):
        # ... existing init code ...
        
        # Add intent system
        self.intent_classifier = None
        self.intent_handlers = None
        self.intent_router = None
    
    async def connect(self) -> bool:
        """Connect to message bus."""
        # ... existing connection code ...
        
        if self.message_bus:
            # Initialize intent system
            self.intent_classifier = IntentClassifier(self.message_bus)
            self.intent_handlers = IntentHandlers(
                self.message_bus,
                context_getter=self._get_context_info
            )
            self.intent_router = IntentRouter(self.intent_handlers)
        
        return self.message_bus is not None
    
    # Add new method for intent-based processing
    async def process_with_intent(self, user_input: str, context: dict = None) -> dict:
        """
        Process user input using intent classification.
        
        Returns:
            {
                "type": "text|command_approval|search_results|error",
                "content": str or dict,
                "needs_approval": bool,
                "pending_action": dict (optional)
            }
        """
        if not self.intent_classifier:
            # Fallback to old method
            return await self._fallback_process(user_input)
        
        # Classify intent
        intent_result = await self.intent_classifier.classify(user_input, context or {})
        
        logger.info(
            "Intent classified",
            intent=intent_result.get("intent"),
            confidence=intent_result.get("confidence")
        )
        
        # Route to handler
        result = await self.intent_router.route(intent_result, user_input)
        
        # Handle special cases that need external services
        if result.get("type") == "needs_external_handler":
            intent = result.get("intent")
            params = result.get("parameters", {})
            
            if intent == IntentType.WEB_SEARCH:
                return await self._handle_web_search(params.get("query", user_input))
            
            elif intent == IntentType.FILE_SEARCH:
                return await self._handle_file_search(params.get("query", user_input))
            
            elif intent == IntentType.SYSTEM_QUERY:
                return await self._handle_system_query()
            
            elif intent == IntentType.OCR_REQUEST:
                return {"type": "ocr_request", "needs_approval": False}
            
            elif intent == IntentType.IMAGE_GEN:
                prompt = params.get("prompt", user_input)
                return {"type": "image_gen", "prompt": prompt, "needs_approval": False}
        
        return result
    
    async def _handle_web_search(self, query: str) -> dict:
        """Handle web search intent."""
        results = await self.web_search(query, num_results=5)
        
        if not results:
            return {
                "type": "text",
                "content": "No web search results found.",
                "needs_approval": False
            }
        
        return {
            "type": "search_results",
            "subtype": "web",
            "content": results,
            "needs_approval": True,  # To open browser
            "pending_action": {
                "type": "open_url",
                "url": results[0].get("url", "")
            }
        }
    
    async def _handle_file_search(self, query: str) -> dict:
        """Handle file search intent."""
        result = await self.search_files(query)
        
        if "error" in result:
            return {
                "type": "error",
                "content": result["error"],
                "needs_approval": False
            }
        
        items = result.get("results", [])
        
        if not items:
            return {
                "type": "text",
                "content": "No files found matching your search.",
                "needs_approval": False
            }
        
        return {
            "type": "search_results",
            "subtype": "files",
            "content": items,
            "needs_approval": True,  # To open file
            "pending_action": {
                "type": "open_file",
                "path": items[0].get("file_path", "")
            }
        }
    
    async def _handle_system_query(self) -> dict:
        """Handle system health query."""
        try:
            summary = await self.message_bus.request(
                "system.health.summary",
                {},
                timeout=5.0
            )
            return {
                "type": "system_health",
                "content": summary,
                "needs_approval": False
            }
        except Exception as e:
            return {
                "type": "error",
                "content": f"Failed to get system health: {e}",
                "needs_approval": False
            }
```

### Step 2: Update Interactive Mode

Replace the brittle `_should_chat` logic with intent classification:

```python
async def interactive_mode(self):
    """Run interactive mode."""
    # ... existing startup code ...
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]aish[/bold green]").strip()
            
            if not user_input:
                continue
            
            # Handle special commands (keep existing /exit, /help, etc.)
            if user_input == "/exit":
                break
            # ... other special commands ...
            
            # NEW: Use intent-based processing
            with console.status("[bold yellow]Thinking...[/bold yellow]"):
                result = await self.process_with_intent(
                    user_input,
                    context={"chat_mode": self.chat_mode}
                )
            
            # Handle result based on type
            result_type = result.get("type")
            
            if result_type == "text":
                # Simple text response
                content = result.get("content", "")
                md = Markdown(content)
                console.print("\n[bold]Assistant:[/bold]")
                console.print(Panel(md, border_style="blue"))
            
            elif result_type == "command_approval":
                # Command needs approval
                command = result.get("content", "")
                console.print("\n[bold]Suggested command:[/bold]")
                syntax = Syntax(command, "bash", theme="monokai", line_numbers=False)
                console.print(syntax)
                
                if Confirm.ask("\nExecute this command?", default=False):
                    await self._execute_command(command)
                else:
                    console.print("[yellow]Command not executed[/yellow]")
            
            elif result_type == "search_results":
                # Display search results
                await self._display_search_results(result)
            
            elif result_type == "system_health":
                # Display health info
                await self._display_health(result.get("content"))
            
            elif result_type == "error":
                console.print(f"[red]Error: {result.get('content')}[/red]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled[/yellow]")
            continue
        except EOFError:
            break
```

### Step 3: Update Voice Assistant

Fix the "I'll run..." issue in the voice assistant:

```python
async def assistant(continuous, duration, language, wake_word):
    """Voice assistant mode."""
    shell = AIShell()
    
    async def run():
        if not await shell.connect():
            return
        
        # ... existing setup code ...
        
        while True:
            # ... recording and STT code ...
            
            # Process with intent system instead of keyword matching
            with console.status("[bold yellow]Thinking...[/bold yellow]"):
                result = await shell.process_with_intent(
                    user_text,
                    context={"voice_mode": True}
                )
            
            result_type = result.get("type")
            
            if result_type == "text":
                # Direct response - no approval needed
                assistant_text = result.get("content", "")
                console.print(f"\n[bold blue]Assistant:[/bold blue] {assistant_text}")
                await shell.speak(assistant_text)
            
            elif result_type == "command_approval":
                # Command needs approval
                command = result.get("content", "")
                assistant_text = f"I'll run: {command}. Should I proceed?"
                console.print(f"\n[bold blue]Assistant:[/bold blue] {assistant_text}")
                await shell.speak(assistant_text)
                
                # Get voice approval
                approval = await _get_voice_approval(shell)
                if approval:
                    await shell._execute_command(command)
                    await shell.speak("Done!")
                else:
                    await shell.speak("Cancelled")
            
            elif result_type == "search_results":
                # Handle search results
                content = result.get("content", [])
                if content:
                    summary = f"I found {len(content)} results. Should I open the first one?"
                    await shell.speak(summary)
                    
                    approval = await _get_voice_approval(shell)
                    if approval:
                        action = result.get("pending_action", {})
                        # Open URL or file
```

### Step 4: Update Overlay Handle Query

Replace overlay's ad-hoc routing with intent system:

```python
async def handle_query(text: str):
    """Handle overlay query with intent classification."""
    shell = AIShell()
    
    if not await shell.connect():
        return "Connection error"
    
    try:
        # Use intent system
        result = await shell.process_with_intent(
            text,
            context={
                "chat_mode": state.get("chat_mode", False),
                "active_app": state.get("active_app")
            }
        )
        
        result_type = result.get("type")
        
        if result_type == "text":
            # Simple text response
            content = result.get("content", "")
            
            # TTS if enabled
            if state.get("tts_enabled"):
                try:
                    await shell.speak(content[:220])
                except:
                    pass
            
            return content
        
        elif result_type == "command_approval":
            # Set pending command
            command = result.get("content", "")
            state["pending"] = {
                "type": "command",
                "data": {"command": command}
            }
            return f"Command ready: {command}\nUse /approve to execute or /cancel to skip."
        
        elif result_type == "search_results":
            # Return formatted search results
            subtype = result.get("subtype")
            content = result.get("content", [])
            pending = result.get("pending_action")
            
            if pending:
                state["pending"] = {
                    "type": "open",
                    "data": pending
                }
            
            if subtype == "web":
                return {
                    "_overlay_render": "web_results",
                    "query": text,
                    "results": content,
                    "pending": pending
                }
            elif subtype == "files":
                return {
                    "_overlay_render": "file_search",
                    "results": content,
                    "pending": pending
                }
        
        elif result_type == "system_health":
            return {
                "_overlay_render": "health",
                "data": result.get("content")
            }
        
        elif result_type == "error":
            return f"Error: {result.get('content')}"
        
        else:
            return "I'm not sure how to handle that request."
    
    except Exception as e:
        logger.error("Handle query error", error=str(e))
        return f"Error: {e}"
    
    finally:
        await shell.disconnect()
```

## Benefits of This Integration

### 1. Consistent Behavior

All input paths (CLI, overlay, voice) use the same intent classification:
- "Hello" → Always handled as greeting
- "What is X?" → Always informational
- "Show me X" → Always command request

### 2. Natural Responses

- **Before**: "Hello!" → Tries to generate a command → Asks for approval
- **After**: "Hello!" → "Hello! How can I help you today?"

- **Before**: "What is Docker?" → Generates command → Asks for approval
- **After**: "What is Docker?" → Educational explanation

- **Before**: "How do I find large files?" → Generates command → Approval
- **After**: "How do I find large files?" → Step-by-step instructions

### 3. Reduced False Positives

The voice assistant won't say "I'll run..." for every input:
- "How are you?" → "I'm running smoothly!"
- "Tell me about SSH" → Explanation
- "Show me large files" → "I'll run: du -sh * | sort -h. Should I proceed?"

### 4. Better Web Search

Web search approval flow is now consistent:
- Text input: Results shown + pending approval
- Voice input: Results shown + pending approval
- Both paths use same logic

### 5. Extensibility

Easy to add new intent types:
1. Add to `IntentType` enum
2. Add handler method
3. Add routing case
4. Done!

## Testing Plan

### Test Cases

```python
test_cases = [
    # Greetings
    ("hello", IntentType.GREETING, False),
    ("hi there!", IntentType.GREETING, False),
    ("how are you?", IntentType.GREETING, False),
    
    # Informational
    ("what is docker?", IntentType.INFORMATIONAL, False),
    ("explain ssh to me", IntentType.INFORMATIONAL, False),
    ("why is the sky blue?", IntentType.INFORMATIONAL, False),
    
    # Command requests
    ("show me large files", IntentType.COMMAND_REQUEST, True),
    ("list running processes", IntentType.COMMAND_REQUEST, True),
    ("find all python files", IntentType.COMMAND_REQUEST, True),
    
    # How-to questions
    ("how do I find large files?", IntentType.COMMAND_HOW_TO, False),
    ("show me how to use grep", IntentType.COMMAND_HOW_TO, False),
    ("what's the best way to compress files?", IntentType.COMMAND_HOW_TO, False),
    
    # Web search
    ("search the web for python tutorials", IntentType.WEB_SEARCH, True),
    ("google latest linux news", IntentType.WEB_SEARCH, True),
    
    # File search
    ("find documents about machine learning", IntentType.FILE_SEARCH, True),
    ("search files containing TODO", IntentType.FILE_SEARCH, True),
    
    # System queries
    ("check system health", IntentType.SYSTEM_QUERY, False),
    ("what's my CPU usage?", IntentType.SYSTEM_QUERY, False),
]

# Run tests
for input_text, expected_intent, expected_approval in test_cases:
    result = await classifier.classify(input_text)
    assert result["intent"] == expected_intent
    assert result["needs_approval"] == expected_approval
    print(f"✓ {input_text}")
```

## Migration Strategy

### Phase 1: Add Intent System (Parallel)

1. Add `intent.py` and `intent_handlers.py` to neuralux common
2. Update setup.py to include new modules
3. Add `process_with_intent()` method to AIShell
4. Keep existing methods intact

### Phase 2: Update One Path at a Time

1. **Start with CLI interactive mode**
   - Update `interactive_mode()` to use intent system
   - Test thoroughly
   - Fall back to old method if issues

2. **Then Voice Assistant**
   - Update `assistant()` command
   - Fix "I'll run..." issue
   - Test conversation flow

3. **Finally Overlay**
   - Update `handle_query()`
   - Test all overlay features
   - Verify web search works

### Phase 3: Remove Old Code

1. Remove `_should_chat()` heuristic
2. Remove ad-hoc keyword matching
3. Clean up redundant code
4. Update documentation

## Configuration

Add configuration options:

```python
# In neuralux/config.py
class NeuraluxConfig:
    # Intent classification
    intent_use_llm: bool = True  # Use LLM for classification
    intent_llm_timeout: float = 10.0  # Timeout for intent classification
    intent_confidence_threshold: float = 0.7  # Minimum confidence
    intent_fallback_enabled: bool = True  # Use heuristic fallback
```

## Monitoring

Add logging for debugging:

```python
logger.info(
    "Intent processed",
    input=user_input[:50],
    intent=result["intent"],
    confidence=result["confidence"],
    needs_approval=result["needs_approval"],
    processing_time_ms=elapsed_ms
)
```

## Performance Expectations

- **Heuristic classification**: < 1ms
- **LLM classification**: 100-300ms (depending on model)
- **Total processing**: 150-400ms (including intent + handler)

The extra 100-300ms for intent classification is worth it for natural behavior.

## Rollback Plan

If issues arise:

1. Set `intent_use_llm = False` to use heuristics only
2. Or add environment variable `DISABLE_INTENT_SYSTEM=true`
3. Falls back to old `_should_chat()` method

## Next Steps

1. Install and test intent system locally
2. Run test suite
3. Update one component at a time
4. Gather user feedback
5. Iterate on prompts and heuristics
6. Consider LangChain multi-agent (Phase 2)

