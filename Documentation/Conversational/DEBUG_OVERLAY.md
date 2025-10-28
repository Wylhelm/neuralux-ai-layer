# Debug: Overlay Timeout vs Standalone Working

## 🔍 Situation

- ✅ **Standalone test works**: `python3 test-conversation-handler.py` completes in 2 seconds
- ❌ **Overlay times out**: Gets "Sorry, an error occurred: timed out"

This means the conversation handler itself is fine, but something in the GTK/overlay integration is causing issues.

## 🐛 Possible Causes

### 1. Event Loop Conflict
The overlay might already have an event loop running (GTK's), and creating a new one causes conflicts.

### 2. Thread/Async Deadlock
GTK main thread + asyncio event loop + background thread = potential deadlock

### 3. NATS Connection Issue
The message bus connection might not be properly shared or might be blocking

## 🔧 Debug Steps

### Step 1: Check Overlay Terminal Output

Restart the overlay and watch for log messages:
```bash
source myenv/bin/activate
aish overlay --hotkey --tray 2>&1 | tee overlay-debug.log
```

When you send "hello", you should see:
```
[info] Processing message input='hello'
```

If you DON'T see this → message not reaching handler
If you see it but nothing after → handler is blocking

### Step 2: Check What Logs Appear

Send "hello" and immediately check the last 20 lines:
```bash
tail -20 overlay-debug.log
```

Look for:
- `Processing message` ← Handler received it
- `planning_actions` ← Action planning started
- `planned_actions` ← Planning completed
- `Message processed successfully` ← Should reach here

### Step 3: Try With Debug Logging

```bash
STRUCTLOG_LEVEL=DEBUG aish overlay --hotkey --tray
```

This will show every step.

## 🚀 Temporary Workaround

While I debug the overlay integration, you can use **traditional mode** which works:

1. Open overlay (Ctrl+Space)
2. **DON'T click 💬** (stay in traditional mode)
3. Type: `hello, can you help me?`
4. Press Enter

This bypasses the conversation handler and uses the simpler single-turn flow.

## 💡 Likely Fix Needed

Based on the symptoms, I suspect we need to:

1. **Use GTK's event loop instead of creating a new one**
2. **Use GLib.idle_add for the entire async operation**
3. **Avoid asyncio.new_event_loop() in GTK context**

Let me create a proper GTK-integrated version...

