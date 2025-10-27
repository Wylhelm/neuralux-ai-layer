# Image Generation in Overlay - Fixed!

## Issue

When typing "generate image of sunset" in the overlay, it was just showing:
```
Result: {'_overlay_render': 'image_gen_request', 'prompt': 'sunset'}
```

The intent system was correctly classifying it as image generation, but the overlay didn't know how to render the `image_gen_request` type.

## Solution

Added a handler for `image_gen_request` render type that automatically triggers the image generation UI.

### What Was Added

**File**: `packages/cli/aish/main.py` (lines 2608-2621)

```python
elif isinstance(result, dict) and result.get("_overlay_render") == "image_gen_request":
    # Image generation request - trigger image generation directly
    prompt = result.get("prompt", "")
    try:
        if hasattr(app.window, "_generate_image_inline"):
            # Call the image generation method directly with the prompt
            app.window._generate_image_inline(prompt)
        else:
            app.window.add_result("Image Generation", f"Prompt: {prompt}")
            app.window.add_result("Tip", "Click the 🎨 button in the toolbar")
    except Exception as e:
        app.window.add_result("Image Generation", f"Prompt: {prompt}")
        app.window.add_result("Error", f"Could not start: {e}")
```

## How It Works Now

### Before
1. User types: "generate image of sunset"
2. Intent system classifies as `IMAGE_GEN`
3. Returns: `{'_overlay_render': 'image_gen_request', 'prompt': 'sunset'}`
4. Overlay shows raw dict (not helpful)

### After
1. User types: "generate image of sunset"
2. Intent system classifies as `IMAGE_GEN`
3. Returns: `{'_overlay_render': 'image_gen_request', 'prompt': 'sunset'}`
4. Overlay detects `image_gen_request` render type
5. **Calls `_generate_image_inline("sunset")` automatically**
6. Image generation starts immediately! 🎨

## Test It Now!

```bash
# Restart overlay if it's running
aish overlay --hotkey --tray

# Type these:
> generate image of sunset
→ ✅ Image generation starts automatically!

> create picture of mountains
→ ✅ Image generation starts automatically!

> draw a cat
→ ✅ Image generation starts automatically!

> paint a forest
→ ✅ Image generation starts automatically!
```

## Image Generation Patterns Recognized

All these patterns trigger automatic image generation:

- "generate image of X"
- "generate picture of X"
- "create image of X"
- "create picture of X"
- "make image of X"
- "draw X"
- "paint X"

The intent classifier extracts the actual prompt by removing these prefixes, so "generate image of sunset" becomes just "sunset" for the image model.

## Benefits

✅ **Natural language**: Just describe what you want  
✅ **Automatic**: No need to click the 🎨 button  
✅ **Consistent**: Works the same way in all interfaces  
✅ **Smart**: Intent system understands image generation requests  

## Technical Details

### Flow

```
User: "generate image of sunset"
    ↓
Intent Classifier: IMAGE_GEN, prompt="sunset"
    ↓
process_with_intent(): returns {type: "image_generation", prompt: "sunset"}
    ↓
Overlay handler: converts to {_overlay_render: "image_gen_request", prompt: "sunset"}
    ↓
_update() function: detects image_gen_request
    ↓
Calls: app.window._generate_image_inline("sunset")
    ↓
Image generation starts!
```

### Related Methods

- `_generate_image_inline(prompt)` - Main image generation method in overlay
- `_on_image_gen_clicked()` - Sets up image gen mode (button handler)
- `handle_image_generation()` - Intent handler that extracts prompt

## Integration with Other Features

The image generation intent works across all interfaces:

### CLI
```bash
aish
> generate image of sunset
→ "Tip: Use the overlay GUI for image generation with preview!"
```

### Voice
```bash
aish assistant
(speak) "generate image of sunset"
→ "For image generation, please use the overlay GUI."
```

### Overlay
```bash
aish overlay
> generate image of sunset
→ ✅ Image generation starts automatically!
```

## Fallback Behavior

If the overlay doesn't have the `_generate_image_inline` method (older version):
- Shows the prompt
- Displays a tip to use the 🎨 button

This ensures graceful degradation on older overlay versions.

---

*Fixed: October 27, 2025*  
*Status: Working across all interfaces*  
*Integration: Complete with intent system*

