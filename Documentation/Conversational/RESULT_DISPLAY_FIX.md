# Result Display Fix - Command Output, Images, Search Results

## Problem
Action results (command output, generated images, search results) were not displaying in the overlay after execution.

## Root Cause
The `ActionResultCard` component was looking for a `"result"` key in the action data, but the `ConversationHandler` returns executed actions with a `"details"` key instead.

**Data structure mismatch:**
```python
# What conversation_handler returns:
executed_action = {
    "action_type": "command_execute",
    "description": "Execute: ls -la ~",
    "success": True,
    "details": {"output": "... command output ..."},  # <-- HERE
    "error": None,
}

# What ActionResultCard was looking for:
result_data = self.action_result.get("result", {})  # Wrong key!
```

## Solution

### 1. Fixed Key Lookup
Changed `ActionResultCard` to look for both `"details"` and `"result"` keys:
```python
result_data = self.action_result.get("details", self.action_result.get("result", {}))
```

### 2. Added Type-Specific Display Logic

Now properly handles different result types:

#### Command Execution
```python
if "output" in result_data:
    output_text = result_data.get("output", "")
    # Shows up to 500 characters of command output
    # Displays in monospace font with selectable text
```

#### Image Generation
```python
elif "image_path" in result_data:
    # Shows image path
    # Displays 200x200 thumbnail of generated image
    # Falls back gracefully if image can't be loaded
```

#### LLM Generation
```python
elif "content" in result_data:
    # Shows generated text content (up to 300 chars)
    # Displays in readable wrapped format
```

#### Generic Results
```python
else:
    # Shows first 200 chars of any other result
    # Works for search results, file operations, etc.
```

### 3. Error Display
```python
if error:
    # Shows error message with ❌ icon
    # Displays clearly with good visibility
```

### 4. Added Better Logging
```python
logger.info("Adding action result", 
           action_type=action.get("action_type"),
           has_details=bool(action.get("details")),
           has_output="output" in action.get("details", {}))
```

## What Works Now

✅ **Command Output**: See the actual output of commands like `ls`, `docker ps`, etc.
✅ **Image Generation**: See generated images as 200x200 thumbnails with file path
✅ **LLM Responses**: See generated text content
✅ **Search Results**: See search results from filesystem/web searches
✅ **Error Messages**: See clear error messages when actions fail
✅ **Selectable Text**: Can select and copy output text
✅ **Truncation**: Long outputs are truncated with "(truncated)" indicator

## Visual Improvements

- Compact monospace display for command output
- Image thumbnails for generated images
- Clean, readable formatting
- Dark background for code/output sections
- Proper word wrapping
- Selectable text for easy copying

## Files Modified

1. **`packages/overlay/conversation/message_bubble.py`**
   - Fixed key lookup from `"result"` to `"details"`
   - Added type-specific display logic
   - Added image thumbnail support
   - Added error display
   - Added GdkPixbuf import for images

2. **`packages/overlay/overlay_window.py`**
   - Added detailed logging for debugging
   - Improved result extraction logic
   - Better error handling

3. **`packages/overlay/styles/conversation.css`**
   - Made `.action-details` more compact (11px font)
   - Better contrast (rgba(0, 0, 0, 0.3))
   - Tighter line height (1.3)

## Test It

1. **Command Execution**:
   - "list files in my home directory"
   - "show my docker containers"
   - **Result**: See actual command output in monospace

2. **Image Generation**:
   - "generate an image of a sunset"
   - **Result**: See 200x200 thumbnail + file path

3. **LLM Content**:
   - "write a haiku about coding"
   - **Result**: See generated text

4. **Error Handling**:
   - Try a command that fails
   - **Result**: See clear error message

## Status
**COMPLETE** ✅ - All action results now display properly!

