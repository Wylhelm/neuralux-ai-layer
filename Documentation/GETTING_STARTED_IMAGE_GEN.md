# Getting Started with Image Generation 🎨

## What's New?

NeuroLux can now generate high-quality images using state-of-the-art Flux AI models! Click a button, describe what you want, and watch as beautiful images appear in seconds.

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
cd /home/guillaume/NeuroTuxLayer/services/vision
pip install -r requirements.txt
```

⏱️ This will take 2-3 minutes and download ~3 GB.

### Step 2: Start the Vision Service

```bash
cd /home/guillaume/NeuroTuxLayer/services/vision
python service.py
```

✅ You should see: "Vision service connected to NATS and handlers registered"

### Step 3: Generate Your First Image

**Option A: Via Overlay (Easiest)**
1. Press `Alt+Space` to open NeuroLux overlay
2. Click the 🎨 (paint palette) button in the top-right
3. Type: "A serene mountain landscape at sunset with dramatic clouds"
4. Click "Generate"
5. Wait ~30 seconds (first time downloads models)
6. Click "Save Image" to save your creation!

**Option B: Via Test Script**
```bash
cd /home/guillaume/NeuroTuxLayer
python scripts/test_image_gen.py "A cute fluffy cat sitting on a windowsill"
```

**Option C: Via Command Line**
```bash
curl -X POST http://localhost:8005/v1/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A majestic dragon flying over mountains",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 4,
    "model": "flux-schnell"
  }' | jq -r '.image_bytes_b64' | base64 -d > dragon.png
```

## Important Notes

### ⏳ First Generation is Slow
The very first time you generate an image, it will download the Flux model (~12 GB). This can take 10-30 minutes depending on your internet speed. **This only happens once!**

After the model is downloaded, generation is fast:
- flux-schnell: 3-10 seconds per image
- flux-dev: 15-60 seconds per image

### 💾 Storage Requirements
- Models: ~15 GB (one-time download)
- Each generated image: ~2-5 MB
- Make sure you have at least 20 GB free disk space

### 🖥️ GPU Recommended
- **With GPU (NVIDIA)**: 3-10 seconds per image ⚡
- **Without GPU (CPU)**: 10-30 minutes per image 🐢

The feature works on both, but CPU generation is impractically slow for regular use.

## Verify Your Setup

### Check if Vision Service is Running
```bash
curl http://localhost:8005/
```

Should return:
```json
{"service": "vision_service", "version": "0.1.0", "status": "running"}
```

### Check GPU Detection
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

If False, you're using CPU (slow but works).

### Check Model Status
```bash
curl http://localhost:8005/v1/model-info | jq
```

## Common Issues & Solutions

### "Connection refused" Error
**Problem**: Vision service isn't running  
**Solution**:
```bash
cd /home/guillaume/NeuroTuxLayer/services/vision
python service.py
```

### "CUDA out of memory" Error
**Problem**: GPU doesn't have enough VRAM  
**Solutions**:
- Use smaller size: 512x512 instead of 1024x1024
- Use flux-schnell instead of flux-dev
- Close other GPU-intensive applications
- Restart the vision service

### Very Slow Generation
**Problem**: Using CPU instead of GPU, or first-time model download  
**Check**:
```bash
# Check if CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# Check service logs for "Loading model" messages
```

### Button Not Appearing in Overlay
**Problem**: Overlay not updated or not running  
**Solution**:
```bash
# Restart the overlay
killall python  # (be careful, this kills all python processes)
# Then start overlay again
```

## Example Prompts

Try these prompts to see what the models can do:

### Landscapes
```
A serene Japanese garden with cherry blossoms and a koi pond, soft morning light
```

### Portraits
```
Professional headshot of a confident businesswoman, studio lighting, shallow depth of field
```

### Fantasy
```
Ancient wizard's tower on a cliff overlooking a stormy sea, magical glow from windows
```

### Abstract
```
Vibrant geometric abstract art, Kandinsky style, bold colors and dynamic shapes
```

### Architecture
```
Modern sustainable eco-house with glass walls, surrounded by forest, architectural photography
```

### Animals
```
Majestic lion with a flowing mane, golden hour lighting, National Geographic style
```

## Tips for Better Results

1. **Be specific**: "A red vintage bicycle leaning against a brick wall" is better than "a bicycle"
2. **Add style keywords**: "cinematic lighting", "oil painting", "photorealistic", "watercolor"
3. **Mention quality**: "high detail", "4K", "professional photography"
4. **Control mood**: "serene", "dramatic", "whimsical", "mysterious"
5. **Iterate**: Generate, refine prompt, regenerate

## Model Comparison

| Model | Speed | Quality | Best For | VRAM |
|-------|-------|---------|----------|------|
| flux-schnell | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Quick iterations | 6GB |
| flux-dev | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Final images | 8GB |
| sdxl-lightning | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Alternative style | 6GB |

## What's Included

### New Files
- `services/vision/image_gen_backend.py` - AI model backend
- `services/vision/requirements.txt` - Dependencies
- `IMAGE_GENERATION.md` - Full documentation
- `IMAGE_GEN_QUICKSTART.md` - Quick start
- `IMAGE_GEN_SUMMARY.md` - Technical summary
- `scripts/test_image_gen.py` - Test script
- `services/vision/README.md` - Service documentation

### Updated Files
- `services/vision/service.py` - Added image generation endpoints
- `services/vision/models.py` - Added request/response models
- `packages/overlay/overlay_window.py` - Added 🎨 button and dialog
- `plan.md` - Updated with image generation status

## Next Steps

1. ✅ **Generate your first image** (see Quick Start above)
2. 📚 **Read the full docs**: `IMAGE_GENERATION.md`
3. 🧪 **Experiment with prompts**: Try different descriptions
4. 🎨 **Try different models**: flux-dev for quality, flux-schnell for speed
5. 💾 **Save your favorites**: Click "Save Image" in the dialog
6. 🚀 **Integrate with your workflow**: Use the REST API or NATS

## Need Help?

- **Full Documentation**: `IMAGE_GENERATION.md`
- **Quick Reference**: `IMAGE_GEN_QUICKSTART.md`
- **Service README**: `services/vision/README.md`
- **Test Script**: `python scripts/test_image_gen.py --help`

## What's Next?

Future enhancements planned:
- Image-to-image generation (modify existing images)
- Inpainting (fill in parts of images)
- ControlNet (control with sketches, poses, etc.)
- Batch generation
- Integration with conversation context
- More model options

---

## Ready to Create?

Open the overlay (`Alt+Space`), click 🎨, and start creating! 

**Remember**: First generation downloads models and takes longer. After that, enjoy near-instant AI art generation! ✨

Happy creating! 🎨🚀

