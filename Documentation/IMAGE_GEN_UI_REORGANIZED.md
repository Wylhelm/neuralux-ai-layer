# Image Generation UI Reorganized 🎨

## What Changed

### ✅ Image Generation Now in Overlay Window

**Before**: Separate dialog window opened  
**After**: Images generate directly in the main overlay window

### ✅ Settings Moved to Tray Settings

**Before**: Settings in separate image generation dialog  
**After**: All image generation settings in the main Settings window (accessible from tray)

## How to Use

### Generate an Image

1. **Open overlay**: Press `Alt+Space`
2. **Click 🎨 button** (top-right)
3. **Enter your prompt** in the search box: "A beautiful mountain landscape at sunset"
4. **Press Enter**
5. **Watch progress** in status bar: "Loading model...", "Generating...", etc.
6. **Image appears** in the results area with a **💾 Save Image** button
7. **Click Save** to download your image

### Configure Settings

1. **Right-click tray icon** → **Settings**  
   OR open overlay and use settings command
2. **Scroll to "Image Generation" section**
3. **Configure**:
   - **Model**: flux-schnell (fast), flux-dev (quality), or sdxl-lightning
   - **Size**: 512x512, 768x768, 1024x768, 768x1024, or 1024x1024
   - **Steps**: 1-50 (4 is default, fast and good quality)
4. **Click Apply** to use immediately
5. **Click Save Defaults** to persist settings

## UI Flow

```
┌─────────────────────────────────────────────────────────┐
│  Overlay Window (Alt+Space)                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │ [🎤] [🔇] [🆕] [🕘] [🔲] [↻] [🎨] ← Click here  │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Describe the image you want to generate...      │   │
│  │ A beautiful sunset over mountains ← Type        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Status: Generating 1024x1024 image (4 steps)...      │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │         🖼️ [Generated Image Here]                │   │
│  │                                                   │   │
│  │         [💾 Save Image]  ← Click to save        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Settings Window

```
┌─────────────────────────────────────────────────────────┐
│  Settings                                      [×]       │
├─────────────────────────────────────────────────────────┤
│  LLM model file: [llama-3.2-3b-instruct-q4_k_m.gguf ]   │
│  Quick select: [Llama 3B] [Mistral 7B]                  │
│  [Download Mistral 7B Q4_K_M]                           │
│                                                          │
│  STT model: [medium ▼]                                  │
│                                                          │
│  ─────────────────────────────────────                  │
│  Image Generation                                        │
│  ─────────────────────────────────────                  │
│  Model: [flux-schnell (fast) ▼]                        │
│  Size: [1024x1024 ▼]                                    │
│  Steps: [4]                                              │
│                                                          │
│  [Apply] [Save Defaults] [Close]                        │
└─────────────────────────────────────────────────────────┘
```

## Features

### Progress Tracking
- Real-time progress in status bar
- Shows:
  - "Loading flux-schnell model..."
  - "Downloading model (if needed)..."
  - "Generating 1024x1024 image..."
  - "Running diffusion process..."
  - "✓ Image generated successfully!"

### Image Display
- Full image preview in overlay
- Scales to fit results area
- Click to view full size

### Save Functionality
- Click **💾 Save Image** button
- File dialog opens
- Auto-suggested filename from prompt
- Format: `{prompt}_{timestamp}.png`
- Example: `beautiful_sunset_20251026_152030.png`

### Settings Persistence
- Settings saved to disk
- Applied to all future generations
- Can change anytime from tray menu

## Workflow Examples

### Quick Generation (Default Settings)
```
1. Alt+Space
2. Click 🎨
3. Type: "a cute cat"
4. Press Enter
5. Wait 5-10 seconds
6. Click Save
```

### Custom Generation (With Settings)
```
1. Right-click tray → Settings
2. Change:
   - Size: 768x768 (faster)
   - Steps: 4
   - Model: flux-schnell
3. Click Save Defaults
4. Alt+Space
5. Click 🎨
6. Type prompt
7. Press Enter
8. Save image
```

### Batch Generation
```
1. Alt+Space → Click 🎨
2. Type prompt 1 → Enter → Wait → Save
3. Click 🎨 again
4. Type prompt 2 → Enter → Wait → Save
5. Repeat!
```

## Benefits of New UI

✅ **Faster workflow** - No separate windows  
✅ **Cleaner interface** - One unified window  
✅ **Better visibility** - Image shows in main area  
✅ **Settings organized** - All settings in one place  
✅ **Less clicking** - Direct from overlay to image  
✅ **Progress visible** - Always see what's happening  
✅ **Persistent settings** - Configure once, use everywhere  

## Technical Details

### Memory Usage
- **8-bit quantized Flux**: ~900 MB VRAM (when generating)
- **CPU offloading**: Model on CPU when idle, GPU when generating
- **Efficient**: Can run alongside LLM and audio services

### Performance
- **First time**: ~30 seconds (model loads from CPU to GPU)
- **Subsequent**: 3-10 seconds per image
- **Quality**: Excellent with flux-schnell at 4 steps

### File Management
- **Temp files**: Auto-cleaned after display
- **Saved files**: User chooses location
- **Format**: PNG (high quality)

## Shortcuts

| Action | Method |
|--------|--------|
| Open image gen mode | Click 🎨 in overlay |
| Generate | Type prompt, press Enter |
| Save image | Click 💾 Save Image button |
| Settings | Tray icon → Settings |
| Cancel generation | Esc (closes overlay) |
| New generation | Click 🎨 again |

## Tips

1. **Be specific**: "A red vintage bicycle leaning against a brick wall" is better than "a bicycle"
2. **Add style**: "...cinematic lighting", "oil painting", "photorealistic"
3. **Iterate quickly**: flux-schnell at 4 steps is fast enough to experiment
4. **Use 512x512 for speed**: 2-3x faster than 1024x1024
5. **Save good settings**: Configure once in Settings, use everywhere

## Troubleshooting

### Image doesn't appear
- Check status bar for errors
- View logs: `tail -f data/logs/vision-service.log`
- Ensure vision service is running: `curl http://localhost:8005/`

### Out of memory
- Use smaller size (512x512)
- Close other GPU apps
- Restart services: `make stop-all && make start-all`

### Slow generation
- First run loads model (30 sec)
- Check GPU usage: `nvidia-smi`
- Reduce size or steps in Settings

## Summary

**The new UI is:**
- ✨ Simpler and faster
- 🎨 More integrated
- ⚙️ Better organized
- 💾 Easier to save
- 📊 More transparent (progress visible)

**Try it now!**
```bash
# If not running, start all services
make start-all

# Open overlay
Alt+Space

# Click 🎨, type prompt, press Enter!
```

Enjoy your new streamlined image generation experience! 🚀

