# Agent Intelligence Analysis & Improvement Plan

## Executive Summary

The current AI agent implementation suffers from **brittle intent classification** using keyword matching, leading to inconsistent and unnatural behavior. This document analyzes the core issues and proposes a comprehensive solution using **intent-based routing** with optional multi-agent architecture.

## Current Problems Identified

### 1. Inconsistent Intent Classification

**Issue**: Multiple conflicting heuristics scattered throughout the codebase:

- `_should_chat()` (line 440): Only checks for question words ("what", "why", etc.) or "?"
- Overlay greeting detection (line 2174): Checks for "hi", "hello", "hey", etc.
- Voice `is_command_request` (line 2690): Checks for action words ("show", "list", "find", etc.)
- Each path uses different criteria

**Impact**:
- "Hello!" → Treated as command request (no match in `_should_chat`)
- "Show me files" → Sometimes asks for approval, sometimes gives instructions
- Inconsistent user experience across CLI, overlay, and voice

### 2. Web Search Browser Opening Bug

**Location**: Lines 1946-1952 and 2079

**Issue**: 
- Text-based `/web` command sets a pending action but doesn't trigger approval flow
- Voice-based web search also sets pending but the overlay may not display the approval correctly
- The approval rendering logic may not be consistent

**Root Cause**: Approval flow is inconsistent between text and voice inputs

### 3. Voice "I'll run..." False Positives

**Location**: Lines 2690-2699

**Issue**: The `is_command_request` check triggers on ANY occurrence of action words:
```python
is_command_request = any(word in user_text.lower() for word in [
    "show", "list", "find", "search", "create", "delete", "run",
    "execute", "check", "get", "display", "open", "edit", "install"
])
```

**False Positives**:
- "Can you show me how SSH works?" → Treated as command (contains "show")
- "What's the best way to find files?" → Treated as command (contains "find")
- "How do I check if a port is open?" → Treated as command (contains "check" and "open")

### 4. No Contextual Understanding

**Issue**: The LLM is always asked for a command in command mode, even when the request is informational:
- "Hello!" → LLM tries to generate a command
- "What is Docker?" → LLM generates command instead of explaining

**Impact**: Unnecessary approval requests for simple greetings or questions

## Proposed Solution: Intent-Based Agent Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User Input                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                Intent Classifier Agent                       │
│  (Small, fast LLM call with structured output)              │
│  Returns: intent_type + confidence + extracted_params       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Intent Router                             │
│  Routes to specialized handlers based on intent              │
└────────┬────────┬─────────┬──────────┬──────────┬───────────┘
         │        │         │          │          │
         ▼        ▼         ▼          ▼          ▼
    ┌────────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌──────────┐
    │Greeting│ │Query │ │Command │ │Search│ │System    │
    │Handler │ │Agent │ │Agent   │ │Agent │ │Action    │
    └────────┘ └──────┘ └────────┘ └──────┘ └──────────┘
```

### Intent Types & Handlers

| Intent | Description | Examples | Needs Approval? | Handler |
|--------|-------------|----------|-----------------|---------|
| `greeting` | Social pleasantries | "hello", "hi", "how are you" | No | Direct response |
| `informational` | Knowledge questions | "what is X?", "explain Y" | No | Query Agent |
| `command_request` | Wants to execute action | "show large files", "list processes" | Yes | Command Agent |
| `web_search` | Internet search | "search web for X", "google Y" | Yes (to open) | Search Agent |
| `file_search` | Local file search | "find documents about X" | Maybe | Search Agent |
| `system_query` | System status | "check health", "CPU usage" | No | System Handler |
| `ocr_request` | Vision/OCR | "OCR window", "read text" | No | Vision Handler |
| `conversation` | Follow-up in chat mode | Any text when in chat mode | No | Conversational Agent |

### Implementation Strategy

#### Phase 1: Intent Classifier (Recommended - Simple & Effective)

Add a lightweight intent classification step before routing:

```python
async def classify_intent(self, user_input: str, context: dict) -> dict:
    """
    Classify user intent using LLM with structured output.
    
    Returns:
        {
            "intent": "greeting|informational|command_request|web_search|...",
            "confidence": 0.0-1.0,
            "parameters": {...},  # Extracted params like search query, file path, etc.
            "reasoning": "why this intent was chosen"
        }
    """
    system_prompt = """You are an intent classifier for a Linux AI assistant.
Analyze the user's input and classify it into ONE of these intents:

1. greeting: Social pleasantries, greetings, small talk
   Examples: "hello", "hi", "how are you", "good morning"

2. informational: Questions seeking knowledge or explanations
   Examples: "what is docker?", "explain SSH", "how does git work?"

3. command_request: User wants to execute a system command
   Examples: "show large files", "list running processes", "create directory"
   Key: User wants an ACTION to be performed NOW

4. command_how_to: User asking HOW to do something (not requesting action)
   Examples: "how do I find large files?", "show me how to use grep"
   Key: User wants INSTRUCTIONS, not execution

5. web_search: User wants to search the internet
   Examples: "search web for X", "google Y", "look up Z online"

6. file_search: User wants to search local files
   Examples: "find documents about X", "search files containing Y"

7. system_query: User wants system status/health info
   Examples: "check system health", "CPU usage", "memory status"

8. ocr_request: User wants OCR/vision
   Examples: "OCR window", "read text from screen"

9. conversation: Continuing a conversation (when in chat mode)
   Context: Previous context suggests ongoing dialogue

Respond ONLY with valid JSON:
{
    "intent": "<intent_type>",
    "confidence": 0.95,
    "parameters": {
        "query": "extracted search query or command description",
        "target": "file/web/system"
    },
    "reasoning": "Brief explanation"
}

Current context:
- Chat mode: {chat_mode}
- Previous context: {prev_context}
"""

    messages = [
        {"role": "system", "content": system_prompt.format(
            chat_mode=context.get("chat_mode", False),
            prev_context=context.get("prev_context", "none")
        )},
        {"role": "user", "content": user_input}
    ]
    
    # Use low temperature for consistent classification
    response = await self.message_bus.request("ai.llm.request", {
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 200
    })
    
    try:
        return json.loads(response.get("content", "{}"))
    except:
        # Fallback to heuristics if JSON parsing fails
        return self._fallback_classify(user_input)
```

#### Phase 2: Specialized Handlers

```python
async def handle_greeting(self, user_input: str) -> str:
    """Handle greetings - no LLM needed for simple cases."""
    greetings = {
        "hello": "Hello! How can I help you today?",
        "hi": "Hi there! What can I do for you?",
        "hey": "Hey! Ready to assist you.",
        "good morning": "Good morning! What would you like to do?",
        "good afternoon": "Good afternoon! How can I help?",
    }
    
    simple = user_input.lower().strip().rstrip('!.')
    if simple in greetings:
        return greetings[simple]
    
    # For more complex greetings, use LLM
    return await self.ask_llm(user_input, mode="chat")


async def handle_informational(self, user_input: str, context: dict) -> str:
    """Handle knowledge questions - no approval needed."""
    system_prompt = """You are a helpful Linux expert assistant.
Provide clear, accurate, educational answers.
If the question involves running a command, EXPLAIN how to do it, don't just give the command.

Current context: {context}
"""
    
    response = await self.message_bus.request("ai.llm.request", {
        "messages": [
            {"role": "system", "content": system_prompt.format(context=context)},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.4,
        "max_tokens": 500
    })
    
    return response.get("content", "")


async def handle_command_request(self, user_input: str, context: dict) -> dict:
    """Handle command requests - needs approval."""
    # Use existing command generation logic
    command = await self.ask_llm(user_input, mode="command")
    
    return {
        "type": "command_approval",
        "command": command,
        "explanation": f"Generated command for: {user_input}",
        "needs_approval": True
    }


async def handle_command_how_to(self, user_input: str, context: dict) -> str:
    """Handle 'how to' questions - provide instructions, not commands."""
    system_prompt = """You are a helpful Linux instructor.
The user is asking HOW to do something, not requesting you do it.
Provide step-by-step instructions with example commands, but make it clear these are examples to learn from.

Format your response as:
1. Brief explanation of what they want to achieve
2. Step-by-step instructions
3. Example commands with explanations
4. Alternative approaches if applicable

Current context: {context}
"""
    
    response = await self.message_bus.request("ai.llm.request", {
        "messages": [
            {"role": "system", "content": system_prompt.format(context=context)},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.5,
        "max_tokens": 600
    })
    
    return response.get("content", "")
```

#### Phase 3: Unified Routing

```python
async def process_user_input(self, user_input: str, context: dict = None) -> dict:
    """
    Main entry point for processing user input.
    
    Returns:
        {
            "type": "text|command_approval|search_results|error",
            "content": "response text or data",
            "needs_approval": bool,
            "pending_action": {...} if applicable
        }
    """
    context = context or {}
    
    # Step 1: Classify intent
    intent_result = await self.classify_intent(user_input, context)
    intent = intent_result.get("intent")
    confidence = intent_result.get("confidence", 0.0)
    params = intent_result.get("parameters", {})
    
    logger.info(f"Intent classified", intent=intent, confidence=confidence)
    
    # Step 2: Route to appropriate handler
    if intent == "greeting":
        content = await self.handle_greeting(user_input)
        return {"type": "text", "content": content, "needs_approval": False}
    
    elif intent == "informational":
        content = await self.handle_informational(user_input, context)
        return {"type": "text", "content": content, "needs_approval": False}
    
    elif intent == "command_request":
        result = await self.handle_command_request(user_input, context)
        return result
    
    elif intent == "command_how_to":
        content = await self.handle_command_how_to(user_input, context)
        return {"type": "text", "content": content, "needs_approval": False}
    
    elif intent == "web_search":
        query = params.get("query", user_input)
        results = await self.web_search(query)
        return {
            "type": "search_results",
            "content": results,
            "needs_approval": True,  # To open browser
            "pending_action": {"type": "open_url", "url": results[0]["url"]} if results else None
        }
    
    elif intent == "file_search":
        query = params.get("query", user_input)
        results = await self.search_files(query)
        return {
            "type": "search_results",
            "content": results,
            "needs_approval": True,  # To open file
            "pending_action": {"type": "open_file", "path": results[0]["path"]} if results else None
        }
    
    elif intent == "system_query":
        content = await self.handle_system_query(user_input)
        return {"type": "text", "content": content, "needs_approval": False}
    
    elif intent == "conversation":
        # Use conversational agent with history
        content = await self.handle_conversation(user_input, context)
        return {"type": "text", "content": content, "needs_approval": False}
    
    else:
        # Fallback to conversational
        content = await self.ask_llm(user_input, mode="chat")
        return {"type": "text", "content": content, "needs_approval": False}
```

### Phase 4: Multi-Agent with LangChain (Optional Enhancement)

For even more sophisticated behavior, implement specialized agents using LangChain:

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_community.chat_models import ChatLlamaCpp

class NeuraluxAgentSystem:
    """Multi-agent system using LangChain."""
    
    def __init__(self):
        self.llm = self._init_llm()
        self.tools = self._init_tools()
        
        # Specialized agents
        self.command_agent = self._create_command_agent()
        self.research_agent = self._create_research_agent()
        self.system_agent = self._create_system_agent()
    
    def _init_tools(self):
        """Initialize available tools for agents."""
        return [
            Tool(
                name="execute_command",
                func=self._execute_command_tool,
                description="Execute a shell command (requires approval)"
            ),
            Tool(
                name="search_web",
                func=self._web_search_tool,
                description="Search the internet for information"
            ),
            Tool(
                name="search_files",
                func=self._file_search_tool,
                description="Search local files semantically"
            ),
            Tool(
                name="get_system_health",
                func=self._health_tool,
                description="Get current system health metrics"
            ),
            Tool(
                name="ask_user_approval",
                func=self._approval_tool,
                description="Ask user for approval before taking action"
            )
        ]
    
    def _create_command_agent(self):
        """Agent specialized in generating and executing commands."""
        prompt = """You are a Linux command expert.
Your job is to help users accomplish tasks through shell commands.

When the user requests an action:
1. Determine the appropriate shell command
2. Use ask_user_approval to get confirmation
3. Use execute_command to run it
4. Report the results

Available tools: {tools}
"""
        return create_react_agent(self.llm, self.tools, prompt)
    
    def _create_research_agent(self):
        """Agent specialized in answering questions."""
        prompt = """You are a helpful research assistant.
Your job is to answer questions using available tools.

When the user asks a question:
1. Determine if you need external information
2. Use search_web or search_files if needed
3. Synthesize a clear, helpful answer

Available tools: {tools}
"""
        return create_react_agent(self.llm, self.tools, prompt)
```

## Implementation Roadmap

### Quick Win: Intent Classification (1-2 days)

1. ✅ Implement `classify_intent()` function
2. ✅ Create specialized handlers for each intent type
3. ✅ Update `process_user_input()` to use intent routing
4. ✅ Add logging for intent classification debugging
5. ✅ Test with common user inputs

**Files to modify**:
- `packages/cli/aish/main.py` - Add intent classification
- `packages/overlay/overlay_window.py` - Use new routing in overlay

### Medium Term: Consistent Approval Flow (3-5 days)

1. ✅ Standardize approval data structure
2. ✅ Unify approval UI across CLI, overlay, voice
3. ✅ Fix web search browser opening
4. ✅ Add approval timeout (auto-cancel after 30s)

### Long Term: Multi-Agent with LangChain (1-2 weeks)

1. Add LangChain dependencies
2. Implement agent system
3. Create tools for agents
4. Add memory/context persistence
5. Implement agent coordination
6. Performance optimization

## Benefits of This Approach

### 1. Natural Behavior
- "Hello" → Friendly response, no command generation
- "What is Docker?" → Educational explanation
- "Show me large files" → Command with approval

### 2. Consistent Experience
- Same logic across CLI, overlay, voice
- Predictable approval flow
- Clear separation of concerns

### 3. Extensibility
- Easy to add new intent types
- Can swap out handlers
- LangChain integration path clear

### 4. Debuggability
- Intent classification logged
- Clear routing path
- Confidence scores for monitoring

### 5. Performance
- Intent classification is fast (~100-200ms)
- Can cache common patterns
- Avoids unnecessary LLM calls for simple cases

## Metrics to Track

After implementation, track these metrics:

1. **Intent Classification Accuracy**
   - % of correctly classified intents (user feedback)
   - Average confidence score
   - Fallback rate

2. **User Experience**
   - False approval requests (should be near 0%)
   - Time to response for different intent types
   - User satisfaction ratings

3. **Performance**
   - Intent classification latency
   - End-to-end response time
   - LLM API call count reduction

## Conclusion

The current implementation's brittleness stems from keyword-based heuristics. Moving to **intent-based routing with LLM classification** will make the agent feel significantly more intelligent and natural. 

**Recommended Path**: Start with Phase 1 (intent classification) for immediate improvement, then consider LangChain multi-agent if more sophisticated behavior is needed.

The intent classifier acts as a "traffic cop" that understands what the user wants and routes to the appropriate specialist, rather than trying to force every input through command generation.

