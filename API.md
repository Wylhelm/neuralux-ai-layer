# Neuralux API Reference (Phase 2A/2B)

## Health Service

### REST

- GET `/health` → Current snapshot
- GET `/history?start=<iso>&end=<iso>&interval=<sec>` → Time-range metrics

Response (abridged):

```json
{
  "status": "healthy|warning|critical",
  "current_metrics": {
    "cpu": { "usage_percent": 12.3, "per_core": [], "load_average": [0.12, 0.20, 0.25] },
    "memory": { "total": 0, "used": 0, "percent": 0 },
    "disks": [ { "mountpoint": "/", "used": 0, "free": 0, "percent": 0 } ],
    "network": { "bytes_sent": 0, "bytes_recv": 0, "connections": 0 },
    "top_processes": [ { "pid": 0, "name": "", "cpu_percent": 0, "memory_percent": 0 } ]
  },
  "alerts": [ { "level": "warning", "category": "cpu", "message": "", "value": 0, "threshold": 0 } ]
}
```

### NATS Subjects

- `system.health.current` → Current snapshot
- `system.health.history` → Time-range metrics
- `system.health.alerts` → Recent alerts
- `system.health.summary` → Aggregated health status

Includes NVIDIA GPU metrics (when NVML is available): utilization, VRAM usage, temperature, power.

Example (Python):

```python
response = await message_bus.request("system.health.summary", {}, timeout=5.0)
```

## Audio Service

### REST

- GET `/` → Service info
- GET `/info` → Detailed service information and models
- POST `/stt` → Speech-to-text transcription
- POST `/stt/file` → Upload audio file for transcription
- POST `/tts` → Text-to-speech synthesis (returns JSON with base64 audio)
- POST `/tts/audio` → Text-to-speech synthesis (returns audio file)
- POST `/vad` → Voice activity detection

**STT Request:**
```json
{
  "audio_path": "/path/to/audio.wav",  // OR audio_data (base64)
  "language": "en",                     // or "auto"
  "task": "transcribe",                 // or "translate"
  "vad_filter": true,
  "word_timestamps": false
}
```

**TTS Request:**
```json
{
  "text": "Hello, world!",
  "voice": "en_US-lessac-medium",       // optional
  "speed": 1.0,                         // 0.5-2.0
  "output_format": "wav"
}
```

**VAD Request:**
```json
{
  "audio_path": "/path/to/audio.wav",  // OR audio_data (base64)
  "threshold": 0.5                      // 0.0-1.0
}
```

### NATS Subjects

- `ai.audio.stt` → Speech-to-text
- `ai.audio.tts` → Text-to-speech
- `ai.audio.vad` → Voice activity detection
- `ai.audio.info` → Service information

Example (Python):

```python
# Speech-to-text
response = await message_bus.request("ai.audio.stt", {
    "audio_path": "/path/to/recording.wav",
    "language": "en"
}, timeout=60.0)

# Text-to-speech
response = await message_bus.request("ai.audio.tts", {
    "text": "Hello from Neuralux!",
    "speed": 1.2
}, timeout=30.0)
```

## Overlay Control (NATS)

- `ui.overlay.toggle`
- `ui.overlay.show`
- `ui.overlay.hide`
- `ui.overlay.quit`

CLI helpers:

```bash
# Send control signals
aish overlay --toggle
aish overlay --show
aish overlay --hide
```

## Web Search (CLI/Overlay)

The `aish` shell provides a `/web <query>` command and the overlay supports `/web` and voice phrases like “search the web for <query>”. Results show title, URL, and summary; opening a URL requires explicit approval in the overlay.

## Vision Service (OCR)

### REST

- POST `/v1/ocr` → Run OCR on an image path or base64 image

Request:
```json
{
  "image_path": "/path/to/image.png",   // optional, file path
  "image_bytes_b64": "...",             // optional, base64 PNG/JPEG
  "language": "en"                      // optional, hint (e.g. "en", "fr")
}
```

Response:
```json
{
  "text": "recognized text...",
  "confidence": 0.93,             // average when available
  "words": ["token1", "token2"]  // optional
}
```

Notes:
- Primary engine: PaddleOCR (if installed); fallback: Tesseract
- GPU acceleration is supported via PaddlePaddle GPU builds where available

### NATS Subjects

- `ai.vision.ocr.request` → Request/Reply OCR
- `ai.vision.ocr.result` → Published after each handled OCR request (fire-and-forget)

Example (Python):
```python
resp = await message_bus.request("ai.vision.ocr.request", {
    "image_path": "/tmp/screenshot.png",
    "language": "en"
}, timeout=20.0)
text = resp.get("text", "")
```
