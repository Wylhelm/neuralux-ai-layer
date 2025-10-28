# Timeout Issue - Diagnosis and Fix

## 🔍 The Problem

Getting "Sorry, an error occurred: timed out" in the overlay conversation mode.

## 🐛 Root Cause

The issue was with my timeout protection mechanism. I added `ThreadPoolExecutor` which was creating event loop conflicts. The conversation handler needs a simpler async execution model.

## ✅ Fix Applied

Simplified the async execution to avoid event loop conflicts:
1. Removed `ThreadPoolExecutor` wrapper
2. Added timeout directly at the asyncio level (25 seconds)
3. Improved task cleanup

**File**: `packages/overlay/conversation/handler.py`

## 🚀 Apply the Fix

### Step 1: Restart the overlay

```bash
# Press Ctrl+C in the terminal running the overlay

# Restart:
source myenv/bin/activate
aish overlay --hotkey --tray
```

Look for: `✓ Message bus connected for conversational mode`

### Step 2: Test conversation

1. Press **Ctrl+Space**
2. Click **💬**  
3. Type: `hello`
4. Press **Enter**

**Expected**: Should respond within 2-3 seconds (not timeout)

## 🧪 Verify the Handler Works

Run the test script first to confirm:
```bash
python3 test-conversation-handler.py
```

Should complete in ~2 seconds showing the AI response.

## 🔧 If Still Timing Out

### Check 1: Terminal Output
In the overlay terminal, look for:
```
2025-10-27 XX:XX:XX [info] Processing message input='hello'
2025-10-27 XX:XX:XX [info] planning_actions
2025-10-27 XX:XX:XX [info] Message processed successfully
```

If you see "planning_actions" but it stops there → LLM planning is hanging

### Check 2: LLM Service Response Time
Test the LLM directly:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "hello"}],
    "max_tokens": 100
  }'
```

Should respond in <5 seconds.

### Check 3: Increase Timeout
If your LLM is just slow, increase the timeout in `packages/overlay/conversation/handler.py`:

Find line:
```python
return loop.run_until_complete(asyncio.wait_for(coro, timeout=25.0))
```

Change to:
```python
return loop.run_until_complete(asyncio.wait_for(coro, timeout=60.0))
```

Then restart overlay.

### Check 4: Use Traditional Mode
If conversation mode keeps timing out, use traditional overlay mode:
- Don't click the 💬 button
- Just type your questions normally
- This bypasses the conversation handler

## 📊 Understanding the Timeout Chain

```
User Message
    ↓
[Overlay] Creates background thread
    ↓
[Handler] _run_async creates new event loop
    ↓
[Handler] asyncio.wait_for(..., timeout=25s)  ← Timeout here
    ↓
[ConversationHandler] process_message()
    ↓
[ActionPlanner] plan_actions() → LLM call ← Usually slowest part
    ↓
[ActionOrchestrator] execute_action()
    ↓
[Result] Back to overlay
```

Most timeouts happen at the "plan_actions" LLM call.

## 🎯 Quick Test Workflow

**Test 1**: Simple message
```
> hello
```
Expected: Quick response (~2 seconds)

**Test 2**: File operation
```
> create a file test.txt
```
Expected: Approval dialog appears (~3 seconds)

**Test 3**: Complex request
```
> create a file and write a story about AI in it
```
Expected: Approval dialog with 2 actions (~5 seconds)

## ⚡ Performance Expectations

- **Simple chat**: 1-3 seconds
- **File operations**: 2-5 seconds  
- **Image generation**: 10-30 seconds
- **Complex multi-step**: 5-10 seconds

If taking >25 seconds for simple chat → LLM is too slow or stuck

## 🛠️ Alternative: Disable Action Planning

For faster responses, you can disable the action planning LLM call by using pattern-based planning only. This would require modifying the `ActionPlanner` but is beyond the scope of this fix.

## 📝 Debug Commands

### Watch overlay terminal
Look for these log lines when you send a message:
```bash
[info] Processing message
[info] planning_actions  ← If stuck here, LLM planning issue
[info] Message processed successfully  ← Should reach here
```

### Check LLM service logs
```bash
tail -f data/logs/llm-service.log
```
Should show request coming in and response going out.

### Monitor system resources
```bash
htop
```
Check if LLM process is maxing out CPU (slow) or stuck (0% CPU)

## ✅ Success Indicators

After fix, you should see:
- ✅ Message sent
- ✅ "Thinking..." for 1-3 seconds (not 25+ seconds)
- ✅ AI response appears
- ✅ No timeout errors

## 🎉 Once Working

Try these fun conversations:
```
> tell me a haiku about coding
> what's the weather like on Mars?
> help me brainstorm 5 app ideas
```

---

**If problems persist**, the LLM service itself might need optimization or the model might be too large for your hardware. Consider switching to a faster model in the overlay settings.

