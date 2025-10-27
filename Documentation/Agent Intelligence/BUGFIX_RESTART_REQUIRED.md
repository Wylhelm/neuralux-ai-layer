# Bug Fix: Restart Required + JSON Parsing

## Two Issues Fixed

### 1. Response Handling (Already Fixed) ✅
All handlers now handle both dict and string responses from the LLM service.

### 2. JSON Parsing (Just Fixed) ✅  
The LLM was returning valid JSON but with extra text after it, causing "Extra data" errors.

**Example from your output**:
```json
{
    "intent": "informational",
    "confidence": 0.95,
    ...
} 

Please respond with the appropriate intent...
```

The JSON parser was choking on the text after the closing `}`.

**Fix**: Added smart JSON extraction that finds and parses just the first complete JSON object.

## ⚠️ **CRITICAL: You Must Restart!**

Python caches imported modules. The fixes won't work until you restart `aish`:

```bash
# In your current aish session:
/exit

# Then restart:
aish

# Now test again:
> hello
> what is docker?
> show me large files
> how do I find large files?
> generate image of sunset
```

## What Should Work Now

After restarting, all these should work:

| Input | Expected Behavior |
|-------|-------------------|
| `hello` | ✅ "Hello! How can I help you today?" |
| `what is docker?` | ✅ Educational explanation (no error) |
| `show me large files` | ✅ Command with approval (no error) |
| `how do I find large files?` | ✅ Step-by-step instructions (no error) |
| `generate image of sunset` | ✅ Recognized, directs to overlay |
| `Bonjour!` | ✅ Friendly response |

## Why It Was Failing

1. **Before restart**: Python was using cached old code that didn't handle string responses
2. **JSON parsing**: LLM was returning JSON + extra text, parser couldn't handle it
3. **Fallback worked**: But then handlers failed when called

## Files Modified

- ✅ `packages/common/neuralux/intent.py` - Better JSON parsing
- ✅ `packages/common/neuralux/intent_handlers.py` - Response type handling

## Test Now

```bash
# 1. Exit current session
/exit

# 2. Restart
aish

# 3. Test commands that were failing
> what is docker?
→ Should give explanation

> show me large files in Downloads
→ Should generate command

> how do I find large files?
→ Should give instructions
```

## If Still Failing

If you still get errors after restarting:

1. **Check if services are running**:
   ```bash
   docker-compose ps
   ```

2. **Restart services**:
   ```bash
   make stop-all
   make start-all
   ```

3. **Check LLM service logs**:
   ```bash
   docker-compose logs llm-service
   ```

4. **Try with heuristics only** (bypass LLM classification):
   ```bash
   export INTENT_USE_LLM=false
   aish
   ```

## What's Happening Behind the Scenes

1. **User input** → Intent classifier
2. **Classifier tries LLM** → Times out or returns malformed JSON
3. **Falls back to heuristics** → Works correctly
4. **Routes to handler** → Handler needs to call LLM again
5. **Handler calls LLM** → Gets response (dict or string)
6. **Handler now checks type** → Extracts content correctly ✅

The key fix was making handlers defensive about response types, and making JSON parsing more robust.

---

**TL;DR**: Type `/exit` then `aish` to restart. Everything should work!

