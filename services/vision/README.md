# Vision Service

Neuralux vision service providing OCR and AI image generation capabilities.

## Features

### ✅ Optical Character Recognition (OCR)
- PaddleOCR for accurate text extraction
- Multi-language support
- REST API and NATS message bus integration

### ✅ Image Generation (NEW!)
- **Flux.1-schnell**: Ultra-fast 4-step generation
- **Flux.1-dev**: High-quality detailed generation
- **SDXL-Lightning**: Alternative fast model
- GPU acceleration with automatic CUDA detection
- Memory-efficient with CPU offloading

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

**Note**: First run will download AI models (~12-15 GB). Requires ~20 GB free disk space.

## Running the Service

```bash
python service.py
```

Service will start on `http://localhost:8005` and connect to NATS.

## API Endpoints

### Health Check
```bash
GET /
```

Returns service status.

### OCR
```bash
POST /v1/ocr
```

**Request**:
```json
{
  "image_path": "/path/to/image.png",
  "language": "en"
}
```

Or with base64 image:
```json
{
  "image_bytes_b64": "base64_encoded_image_data",
  "language": "en"
}
```

### Image Generation
```bash
POST /v1/generate-image
```

**Request**:
```json
{
  "prompt": "A serene mountain landscape at sunset",
  "width": 1024,
  "height": 1024,
  "num_inference_steps": 4,
  "model": "flux-schnell"
}
```

**Response**:
```json
{
  "image_bytes_b64": "base64_encoded_png...",
  "prompt": "A serene mountain landscape at sunset",
  "model": "flux-schnell",
  "width": 1024,
  "height": 1024,
  "seed": null
}
```

### Model Info
```bash
GET /v1/model-info
```

Returns current model status and device info.

### Load Model
```bash
POST /v1/load-model?model_name=flux-dev
```

Load a specific image generation model.

## NATS Subjects

- `ai.vision.ocr.request` - OCR request/reply
- `ai.vision.ocr.result` - OCR result events
- `ai.vision.imagegen.request` - Image generation request/reply
- `ai.vision.imagegen.result` - Generation result events
- `ai.vision.imagegen.model_info` - Model info request/reply
- `ai.vision.info` - Service info request/reply

## Configuration

Environment variables (with defaults):

```bash
VISION_SERVICE_NAME=vision_service
VISION_HOST=0.0.0.0
VISION_SERVICE_PORT=8005
VISION_NATS_SUBJECT_PREFIX=ai.vision
```

## Quick Examples

### Generate an Image

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

### Run OCR

```bash
curl -X POST http://localhost:8005/v1/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "/path/to/document.png",
    "language": "en"
  }'
```

### Check Model Status

```bash
curl http://localhost:8005/v1/model-info | jq
```

## System Requirements

### For Image Generation
- **GPU**: NVIDIA GPU with 6GB+ VRAM (recommended)
- **CPU**: Works but very slow (minutes per image)
- **Storage**: 15-20 GB for models
- **RAM**: 16GB+ recommended

### For OCR Only
- **CPU**: Any modern CPU
- **Storage**: ~500 MB
- **RAM**: 4GB+

## Performance

With NVIDIA RTX 3090 (24GB VRAM):
- flux-schnell @ 1024x1024: ~3-5 seconds
- flux-dev @ 1024x1024: ~15-25 seconds

With NVIDIA RTX 3060 (12GB VRAM):
- flux-schnell @ 1024x1024: ~5-10 seconds
- flux-schnell @ 512x512: ~3-5 seconds

## Troubleshooting

### CUDA Out of Memory
- Reduce image size (try 512x512)
- Use flux-schnell instead of flux-dev
- Close other GPU applications

### Slow Generation
- First run downloads models (~12 GB, one-time)
- Check GPU is detected: Look for "cuda" in service logs
- Verify CUDA: `python -c "import torch; print(torch.cuda.is_available())"`

### Service Won't Start
```bash
# Check if port is in use
sudo lsof -i :8005

# Check for missing dependencies
pip install -r requirements.txt
```

## Model Licenses

- **FLUX.1-schnell**: Apache 2.0 (free for commercial use)
- **FLUX.1-dev**: Non-commercial license (requires license for commercial use)
- **SDXL**: CreativeML Open RAIL++-M License

Make sure you comply with model licenses for your use case.

## Further Documentation

- [Full Image Generation Documentation](../../IMAGE_GENERATION.md)
- [Quick Start Guide](../../IMAGE_GEN_QUICKSTART.md)
- [Test Script](../../scripts/test_image_gen.py)

## Architecture

```
┌─────────────────────────────────────┐
│      Vision Service (Port 8005)     │
├─────────────────────────────────────┤
│  FastAPI REST API                   │
│  - /v1/ocr                          │
│  - /v1/generate-image               │
│  - /v1/model-info                   │
│  - /v1/load-model                   │
├─────────────────────────────────────┤
│  NATS Message Bus Integration       │
│  - ai.vision.* subjects             │
├─────────────────────────────────────┤
│  Backends                           │
│  - OCRProcessor (PaddleOCR)        │
│  - ImageGenerationBackend (Flux)    │
└─────────────────────────────────────┘
```

## Contributing

When adding new vision capabilities:

1. Add backend in `*_backend.py`
2. Add models in `models.py`
3. Add endpoints in `service.py`
4. Add NATS handlers
5. Update this README
6. Add tests

## Support

- GitHub Issues: [Report bugs](https://github.com/your-repo/issues)
- Discussions: [Ask questions](https://github.com/your-repo/discussions)
- Documentation: See main NeuroLux docs

