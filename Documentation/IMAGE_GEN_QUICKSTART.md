# Image Generation Quick Start Guide

## Prerequisites

- NeuroLux installed and running
- NVIDIA GPU with 6GB+ VRAM (recommended) or CPU (slower)
- ~15-20 GB free disk space for models
- Python 3.10+

## Installation Steps

### 1. Install Dependencies

```bash
cd services/vision
pip install -r requirements.txt
```

This will install PyTorch, diffusers, and other required packages (~2-3 GB download).

### 2. Start the Vision Service

If not already running:

```bash
cd services/vision
python service.py
```

The service will start on `http://localhost:8005`.

### 3. Verify Installation

```bash
# Check if vision service is running
curl http://localhost:8005/

# Should return: {"service": "vision_service", "version": "0.1.0", "status": "running"}
```

## First Image Generation

### Using the Overlay (Easiest)

1. Press `Alt+Space` to open the NeuroLux overlay
2. Click the 🎨 (artist palette) button in the top-right
3. Enter a prompt like: `A majestic mountain landscape at sunset`
4. Click **Generate** (first generation will download models - be patient!)
5. Once generated, click **Save Image** to save to disk

### Using the REST API

```bash
curl -X POST http://localhost:8005/v1/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cute cat sitting on a windowsill",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 4,
    "model": "flux-schnell"
  }' | jq -r '.image_bytes_b64' | base64 -d > cat.png
```

## First-Time Setup Notes

⏳ **First generation is slow**: The Flux model (~12 GB) will be downloaded automatically on first use. This can take 10-30 minutes depending on your internet connection.

📁 **Model cache location**: Models are cached by Hugging Face in `~/.cache/huggingface/`. You can set `HF_HOME` environment variable to change this.

💾 **Disk space**: Ensure you have at least 15-20 GB free for model storage.

🖥️ **GPU detection**: The service automatically detects and uses CUDA if available. Check the logs to confirm GPU usage.

## Testing Different Models

### Flux-schnell (Default - Fast)
```python
{
  "prompt": "A serene Japanese garden with cherry blossoms",
  "model": "flux-schnell",
  "num_inference_steps": 4
}
```

### Flux-dev (High Quality)
```python
{
  "prompt": "A detailed portrait of a wise old wizard",
  "model": "flux-dev",
  "num_inference_steps": 20
}
```

### SDXL-Lightning (Alternative Fast Model)
```python
{
  "prompt": "A futuristic cityscape at night with neon lights",
  "model": "sdxl-lightning",
  "num_inference_steps": 4
}
```

## Troubleshooting

### "Service not running" Error
```bash
# Check if vision service is running
ps aux | grep "vision.*service"

# If not, start it
cd services/vision
python service.py
```

### CUDA Out of Memory
```python
# Try smaller image size
{
  "prompt": "Your prompt here",
  "width": 512,
  "height": 512,
  "num_inference_steps": 4
}
```

### Slow CPU Generation
If you don't have a GPU, generation will be slow (minutes). Consider:
- Using smaller sizes (512x512)
- Using fewer steps (4 minimum)
- Running on a machine with a GPU

### Model Download Fails
If automatic download fails, manually download:
```bash
python -c "
from diffusers import FluxPipeline
import torch
FluxPipeline.from_pretrained(
    'black-forest-labs/FLUX.1-schnell',
    torch_dtype=torch.bfloat16
)
"
```

## Performance Expectations

### With NVIDIA RTX 3090 (24GB VRAM)
- flux-schnell @ 1024x1024: ~3-5 seconds
- flux-dev @ 1024x1024: ~15-25 seconds

### With NVIDIA RTX 3060 (12GB VRAM)
- flux-schnell @ 1024x1024: ~5-10 seconds
- flux-dev @ 1024x1024: ~30-60 seconds

### With CPU (Not Recommended)
- flux-schnell @ 512x512: ~5-10 minutes
- flux-schnell @ 1024x1024: ~15-30 minutes

## Next Steps

1. **Explore prompts**: Try different descriptions to see what works best
2. **Experiment with settings**: Adjust steps, size, and models
3. **Read full documentation**: Check `IMAGE_GENERATION.md` for advanced usage
4. **Join the community**: Share your generated images and prompts!

## Support

- 📖 Full documentation: [IMAGE_GENERATION.md](IMAGE_GENERATION.md)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-repo/discussions)

## License Notice

⚖️ **Important**: 
- FLUX.1-schnell: Apache 2.0 (free for commercial use)
- FLUX.1-dev: Non-commercial license (requires license for commercial use)

Make sure you comply with the model licenses for your use case!

---

Happy generating! 🎨✨

