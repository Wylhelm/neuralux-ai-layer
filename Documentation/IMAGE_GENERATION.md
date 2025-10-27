# Image Generation with Flux AI

## Overview

NeuroLux now supports AI-powered image generation using state-of-the-art Flux models from Black Forest Labs. Generate high-quality images from text descriptions directly through the overlay interface.

## Features

- **Flux.1-schnell**: Ultra-fast 4-step generation (default)
- **Flux.1-dev**: Higher quality with more detailed generation
- **SDXL-Lightning**: Alternative fast generation model
- **Save functionality**: Save generated images with automatic naming
- **Customizable settings**: Control size, steps, and model selection
- **GPU acceleration**: Automatic CUDA support when available

## Usage

### Via Overlay Interface (Recommended)

1. **Open the overlay** with `Alt+Space` (or your configured hotkey)
2. **Click the 🎨 button** in the top-right controls
3. **Enter your prompt** in the text area (describe the image you want)
4. **Adjust settings** (optional):
   - **Size**: Choose from 1024x1024, 1024x768, 768x1024, or 512x512
   - **Model**: Select flux-schnell (fast), flux-dev (quality), or sdxl-lightning
   - **Steps**: Number of denoising steps (4 is fast, 20-50 for quality)
5. **Click Generate** and wait for the image to appear
6. **Click Save Image** to save the generated image to disk

### Via REST API

Generate images programmatically:

```bash
curl -X POST http://localhost:8005/v1/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene mountain landscape at sunset with dramatic clouds",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 4,
    "model": "flux-schnell"
  }'
```

### Via NATS Message Bus

```python
from neuralux.messaging import MessageBusClient
from neuralux.config import NeuraluxConfig
import base64

# Connect to message bus
config = NeuraluxConfig()
client = MessageBusClient(config)
await client.connect()

# Send image generation request
response = await client.request("ai.vision.imagegen.request", {
    "prompt": "A futuristic city with flying cars",
    "width": 1024,
    "height": 768,
    "num_inference_steps": 4,
    "model": "flux-schnell"
})

# Get the base64-encoded image
image_b64 = response.get("image_bytes_b64")
if image_b64:
    # Decode and save
    image_bytes = base64.b64decode(image_b64)
    with open("generated_image.png", "wb") as f:
        f.write(image_bytes)
```

## Models

### Flux.1-schnell (Default)
- **Speed**: ⚡⚡⚡⚡⚡ Ultra-fast (4 steps)
- **Quality**: ⭐⭐⭐⭐
- **VRAM**: ~6-8 GB
- **Best for**: Quick iterations, prototyping, real-time generation

### Flux.1-dev
- **Speed**: ⚡⚡⚡
- **Quality**: ⭐⭐⭐⭐⭐ Highest quality
- **VRAM**: ~8-10 GB
- **Best for**: Final images, detailed artwork, professional use

### SDXL-Lightning
- **Speed**: ⚡⚡⚡⚡
- **Quality**: ⭐⭐⭐⭐
- **VRAM**: ~6-8 GB
- **Best for**: Alternative fast generation, different art style

## Configuration

The image generation backend automatically:
- Detects CUDA availability and uses GPU when possible
- Falls back to CPU if no GPU is available (slower)
- Uses model CPU offloading to save VRAM
- Manages memory efficiently with automatic cleanup

## Installation

The image generation feature requires additional dependencies:

```bash
cd services/vision
pip install -r requirements.txt
```

This will install:
- `torch` - PyTorch for model execution
- `diffusers` - Hugging Face diffusers library (Flux support)
- `transformers` - Required for model loading
- `accelerate` - GPU acceleration utilities
- `safetensors` - Safe model format

**Note**: The Flux models will be downloaded automatically on first use (~12-15 GB total). Ensure you have sufficient disk space and a good internet connection.

## Performance Tips

1. **First-time setup**: The first generation will be slower as models download (~12-15 GB)
2. **GPU recommended**: Image generation on CPU is much slower (minutes vs seconds)
3. **VRAM considerations**:
   - flux-schnell: Minimum 6GB VRAM
   - flux-dev: Minimum 8GB VRAM
   - Use 512x512 if you have limited VRAM
4. **Speed vs Quality**:
   - Use 4 steps for quick previews
   - Use 10-20 steps for final images
   - flux-schnell is pre-distilled, so 4 steps is usually sufficient

## Examples

### Prompt Examples

**Landscapes**:
```
A serene mountain lake at golden hour with pine trees and reflections
```

**Portraits**:
```
Professional headshot of a woman in business attire, studio lighting, shallow depth of field
```

**Artistic**:
```
Abstract geometric composition with vibrant colors, Bauhaus style
```

**Technical**:
```
Detailed technical diagram of a quantum computer, isometric view, blueprint style
```

**Fantasy**:
```
Ancient dragon perched on a crystal castle, magical atmosphere, cinematic lighting
```

## Troubleshooting

### Vision service not responding
```bash
# Check if vision service is running
curl http://localhost:8005/

# Restart the service
cd services/vision
python service.py
```

### Out of memory errors
- Reduce image size (try 512x512)
- Use fewer inference steps
- Close other GPU-intensive applications
- Switch to flux-schnell model

### Slow generation
- First run downloads models (one-time, ~12-15 GB)
- Ensure GPU is being used (check logs)
- Consider upgrading GPU if consistently slow

### Model not downloading
```bash
# Manual download (if automatic fails)
python -c "
from diffusers import FluxPipeline
FluxPipeline.from_pretrained('black-forest-labs/FLUX.1-schnell')
"
```

## API Reference

### ImageGenRequest

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompt` | string | **required** | Text description of the image |
| `negative_prompt` | string | null | What to avoid in the image |
| `width` | int | 1024 | Image width (256-2048) |
| `height` | int | 1024 | Image height (256-2048) |
| `num_inference_steps` | int | 4 | Denoising steps (1-100) |
| `guidance_scale` | float | 7.5 | Prompt adherence (0-20) |
| `seed` | int | null | Random seed for reproducibility |
| `model` | string | "flux-schnell" | Model to use |

### ImageGenResponse

| Field | Type | Description |
|-------|------|-------------|
| `image_bytes_b64` | string | Base64-encoded PNG image |
| `prompt` | string | The prompt that was used |
| `model` | string | The model that was used |
| `seed` | int | The seed (if provided) |
| `width` | int | Image width |
| `height` | int | Image height |

## Future Enhancements

Planned features for future releases:
- Image-to-image generation
- Inpainting and outpainting
- ControlNet integration for pose/depth control
- Style transfer
- Batch generation
- Prompt templates and saved presets
- Integration with other NeuroLux features (context-aware generation)

## License

The image generation integration is part of NeuroLux and is licensed under Apache 2.0.

**Note**: The Flux models have their own licenses:
- FLUX.1-schnell: Apache 2.0
- FLUX.1-dev: Non-commercial license (commercial use requires license from Black Forest Labs)

Please review the model licenses before commercial use.

