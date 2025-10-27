# Bugfix: Voice Greeting Asking for Approval

## Issue
User reported: "This is what happens when I say hello with voice, I hear the llm say I'll run..."

When using voice input in the overlay to say "Hello", the system:
1. ✅ Correctly classified it as a greeting
2. ✅ Generated appropriate response: "Hello Guillaume! I'm here to help you with shell commands. How may I assist you today?"
3. ❌ **Incorrectly asked for approval** to "run" the greeting response as a command

## Screenshot Evidence
The user's screenshot showed:
- **You said**: Hello
- **Result**: Hello Guillaume! I'm here to help you with shell commands. How may I assist you today?
- **Approve command?**: [Approve] [Cancel] buttons

This is wrong - a greeting should NOT need approval!

## Root Cause (ACTUAL)

The real problem was found after the first fix didn't work. There were **TWO separate code paths** for voice input:

### 1. The `/voice` Command Handler (Line 2226) - THE ACTUAL PROBLEM
This is what gets triggered when you click the microphone button (🎤) in the overlay. It was using the **OLD system** that bypassed the intent classifier:

```python
# OLD CODE - Always treats everything as a command!
llm_result = await shell.ask_llm(said, mode="command")
# If the LLM returned a command, set pending approval
if isinstance(llm_result, str) and llm_result and not llm_result.startswith("Error"):
    clean_cmd = shell._normalize_command(llm_result)
    state["pending"] = {"type": "command", "data": {"command": clean_cmd}}
    await shell.speak(f"I'll run: {clean_cmd}. Say approve to continue.")
    return {"_overlay_render": "voice_result", "heard": said, "result": clean_cmd, "pending": {"type": "command"}}
```

**The problem**: It calls `ask_llm(said, mode="command")` which **ALWAYS** tries to generate a command, even for greetings! Then it assumes everything returned is a command that needs approval.

### 2. The `handle_query` Function (Line 2387) - Already Fixed
This handles text queries typed in the overlay and was already using the intent system properly.

## Why the First Fix Didn't Work

Initially, we fixed the `handle_query` function (used for **typed text** in the overlay), but the user was clicking the **microphone button** (🎤), which triggers the `/voice` command handler - a completely different code path!

The `/voice` handler was still using the old `ask_llm(said, mode="command")` approach, which is why the bug persisted.

```python
if result_type == "text":
    content = result.get("content", "")
    if state["tts_enabled"] and content:
        await shell.speak(content[:220])
    return content  # ← Returning plain string
```

The overlay's rendering code then didn't have proper metadata to distinguish between:
- **Simple text responses** (greetings, explanations) - No approval needed
- **Commands that need approval** - Approval needed

This caused ambiguity in how the result was displayed.

## Solution

Replaced the OLD `/voice` handler to use the **intent system** instead of always treating input as commands:

### Before (WRONG):
```python
# Always asks LLM for a command, regardless of input
llm_result = await shell.ask_llm(said, mode="command")
# Assumes everything is a command
if isinstance(llm_result, str) and llm_result:
    state["pending"] = {"type": "command", ...}
    return {..., "pending": {"type": "command"}}
```

### After (CORRECT):
```python
# Use intent system to classify the input first
result = await shell.process_with_intent(
    said,
    context={"voice_mode": True}
)

result_type = result.get("type")

if result_type == "text":
    # Direct text response (greeting, explanation, instructions)
    content = result.get("content", "")
    if state["tts_enabled"] and content:
        await shell.speak(content[:220])
    # Return WITHOUT pending approval
    return {"_overlay_render": "voice_result", "heard": said, "result": content}

elif result_type == "command_approval":
    # Command needs approval
    command = result.get("content", "")
    clean_cmd = shell._normalize_command(command)
    state["pending"] = {"type": "command", ...}
    await shell.speak(f"I'll run: {clean_cmd}. Say approve to continue.")
    # Return WITH pending approval
    return {"_overlay_render": "voice_result", "heard": said, "result": clean_cmd, "pending": {"type": "command"}}

# ... handle other intents (search_results, system_health, image_generation, etc.)
```

**Key changes**:
1. ✅ Uses `process_with_intent()` to classify user input
2. ✅ Only treats `command_approval` results as needing approval
3. ✅ Text responses (greetings, explanations) have NO `pending` field
4. ✅ Handles all intent types (search, health, image gen, errors)

## How the Overlay Rendering Works

The overlay's `_update` function checks for pending actions:

```python
elif isinstance(result, dict) and result.get("_overlay_render") == "voice_result":
    heard = result.get("heard", "")
    app.window.add_result("You said", heard)
    res_text = result.get("result", "")
    app.window.add_result("Result", res_text)
    # If pending command, show approval bar
    pending = result.get("pending")
    if pending and pending.get("type") == "command":  # ← Only shows if pending exists
        app.window.show_pending_action("Approve command?", res_text)
```

Now:
- **Text responses** (greetings): No `pending` → No approval button ✅
- **Commands**: Has `pending: {"type": "command"}` → Shows approval button ✅

## Testing

### Should NOT Ask for Approval ✅

**Voice input in overlay:**
```
🎤 "Hello"
→ "Hello Guillaume! I'm here to help you with shell commands. How may I assist you today?"
→ NO approval button

🎤 "What is Docker?"
→ "Docker is a platform for developing, shipping, and running applications in containers..."
→ NO approval button

🎤 "Thank you"
→ "You're welcome! Let me know if you need anything else."
→ NO approval button
```

### Should Ask for Approval ✅

**Voice input in overlay:**
```
🎤 "Show me large files"
→ Generated command: find . -type f -size +100M
→ [Approve] [Cancel] buttons ← YES, approval needed

🎤 "List running processes"
→ Generated command: ps aux
→ [Approve] [Cancel] buttons ← YES, approval needed
```

## Files Changed

- `packages/cli/aish/main.py`:
  - Modified `handle_query` function to return properly formatted `voice_result` for text responses
  - Added explicit `_overlay_render` and `heard` fields
  - Removed ambiguity by not including `pending` field for text-only responses

## Related Issues Fixed

This fixes the original user complaint:
- ❌ "When I say hello! sometimes it want to run something and ask me to approve"
- ❌ "The voice always reply with 'I'll run...' but don't necessarily run something"

Now the voice assistant:
- ✅ Only says "I'll run..." when there's actually a command to approve
- ✅ Greetings and informational responses have no approval step
- ✅ Natural conversation feels more natural

## Status

✅ **Complete** - Changes applied and CLI package reinstalled.

## Test It Now!

```bash
aish overlay --hotkey --tray
```

Then use voice input (🎤 button) and say:
1. "Hello" - Should respond naturally, NO approval
2. "What is Linux?" - Should explain, NO approval  
3. "Show me a tree of my home" - Should ask for approval ✅

The voice interface should now feel much more natural! 🎯

