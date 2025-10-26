# Audio Service Guide

The Neuralux Audio Service provides speech-to-text, text-to-speech, and voice activity detection capabilities, enabling voice interaction with your Linux system.

## Features

### ✅ Speech-to-Text (STT)
- **Engine**: faster-whisper (optimized Whisper implementation)
- **Models**: tiny, base, small, medium, large
- **Languages**: Auto-detection or specify language code
- **Features**:
  - Real-time transcription from microphone
  - Transcription from audio files
  - Voice activity detection (VAD)
  - Word-level timestamps
  - Multiple audio format support

### ✅ Text-to-Speech (TTS)
- **Engine**: Piper (fast, neural TTS)
- **Features**:
  - Natural-sounding speech synthesis
  - Multiple voice options
  - Adjustable speech speed
  - Low latency
  - Offline processing

### ✅ Voice Activity Detection (VAD)
- **Engine**: Silero VAD v5
- **Features**:
  - Accurate speech detection
  - Segment-level timestamps
  - Configurable thresholds
  - Removes silence from recordings

## Installation

### Prerequisites

#### Ubuntu/Debian
```bash
# Audio libraries
sudo apt install -y portaudio19-dev libasound2-dev

# Audio playback tools (optional, for aish speak)
sudo apt install -y alsa-utils pulseaudio-utils ffmpeg
```

### Python Dependencies

The audio service dependencies are included in the main `requirements.txt`:

**For CUDA/GPU acceleration (recommended for faster transcription):**
```bash
pip install nvidia-cudnn-cu12
```

The startup scripts automatically configure the cuDNN library path for CUDA support.

```bash
pip install -r requirements.txt
```

Key packages:
- `faster-whisper>=0.10.0` - Speech-to-text
- `piper-tts>=1.2.0` - Text-to-speech
- `torch>=2.0.0` - ML framework
- `torchaudio>=2.0.0` - Audio processing
- `pyaudio>=0.2.13` - Microphone capture

### Download Models

#### STT Models (Whisper)

Models are downloaded automatically on first use. Default: `medium` with `language=auto`. Available sizes:

- **tiny** (~40MB) - Fast, basic accuracy
- **base** (~140MB) - Good balance (default)
- **small** (~460MB) - Better accuracy
- **medium** (~1.5GB) - High accuracy
- **large** (~3GB) - Best accuracy

To pre-download a model:
```bash
mkdir -p models/audio/whisper
cd models/audio/whisper
# Models download automatically on first use
```

#### TTS Models (Piper)

Download Piper voice models from [Rhasspy Piper](https://github.com/rhasspy/piper/releases):

```bash
mkdir -p models/audio/piper
cd models/audio/piper

# Example: English US voice (Lessac, medium quality)
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.json
```

Popular voices:
- **en_US-lessac-medium** - Clear American English
- **en_GB-northern_english_male-medium** - British English
- **fr_FR-siwis-medium** - French
- **de_DE-thorsten-medium** - German

See the [Piper samples page](https://rhasspy.github.io/piper-samples/) to listen to voices.

## Starting the Service

### Manual Start

```bash
cd services/audio
python service.py
```

The service will start on `http://localhost:8006`.

### Automatic Start

```bash
make start-all  # Starts all services including audio
```

### Check Status

```bash
aish status
# Should show: ✓ Audio service: Running
```

## CLI Usage

### Voice Assistant (`aish assistant`)

Interactive voice-activated AI assistant with conversation support:

```bash
# Single turn conversation (speak once, get response, exit)
aish assistant

# Continuous conversation mode (speak multiple times, say "goodbye" to exit)
aish assistant -c

# Custom recording duration per turn
aish assistant -d 10              # 10 seconds per turn

# Force specific language
aish assistant -l fr              # French conversation
```

**Features:**
- **Bidirectional voice**: Listen and respond with voice
- **LLM integration**: Natural language understanding
- **Conversation context**: Remembers last 3 conversation turns
- **Command execution**: Translates voice requests to shell commands
- **Command approval**: Voice-based yes/no confirmation before execution
- **Auto language detection**: Detects and responds in user's language
- **Exit keywords**: Say "exit", "quit", "goodbye", "bye", "stop", "end", "finish", "close" to end session

**Example conversation:**

```
You: "Show me the files in this directory"
Assistant: "I'll run the command: ls -la. Should I proceed?"
You: "Yes"
Assistant: "Okay, executing now"
[Command executes and output is shown]
Assistant: "Here are the first results: total 184. drwxr-xr-x 15 user..."
```

**Command capabilities:**
The assistant can execute the same commands as `aish ask`, including:
- File operations: list, find, search, create, delete
- System queries: disk space, processes, system info
- Text processing: grep, find, sort
- And any other shell commands you request!

### Text-to-Speech (`aish speak`)

Convert text to speech:

```bash
# Basic usage
aish speak "Hello, world!"

# Adjust speech speed
aish speak "This is faster" --speed 1.5
aish speak "This is slower" --speed 0.7

# Save to file instead of playing
aish speak "Save this audio" --output greeting.wav

# Specify voice (if multiple models available)
aish speak "Different voice" --voice en_GB-northern_english_male-medium
```

**Options:**
- `--voice, -v` - Voice model to use
- `--speed, -s` - Speech speed multiplier (0.5-2.0)
- `--output, -o` - Save audio to file
- `--play, -p` - Play audio (default if no --output)

### Speech-to-Text (`aish listen`)

Convert speech to text:

```bash
# Record 5 seconds and transcribe
aish listen

# Record for 10 seconds
aish listen --duration 10

# Transcribe existing audio file
aish listen --file recording.wav

# Specify language (for better accuracy)
aish listen --language fr
aish listen --language es

# Auto-detect language
aish listen --language auto

# Save transcription to file
aish listen --output transcript.txt
```

**Options:**
- `--duration, -d` - Recording duration in seconds (default: 5)
- `--file, -f` - Transcribe from audio file
- `--language, -l` - Language code or "auto"
- `--output, -o` - Save transcription to file

## API Usage

### REST API

The audio service provides HTTP endpoints at `http://localhost:8006`:

#### Speech-to-Text

```bash
# POST /stt
curl -X POST http://localhost:8006/stt \
  -H "Content-Type: application/json" \
  -d '{
    "audio_path": "/path/to/audio.wav",
    "language": "en",
    "vad_filter": true
  }'

# Upload audio file
curl -X POST http://localhost:8006/stt/file \
  -F "file=@recording.wav" \
  -F "language=en"
```

#### Text-to-Speech

```bash
# POST /tts
curl -X POST http://localhost:8006/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "speed": 1.0
  }'

# Get audio file directly
curl -X POST http://localhost:8006/tts/audio \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello!"}' \
  -o speech.wav
```

#### Voice Activity Detection

```bash
# POST /vad
curl -X POST http://localhost:8006/vad \
  -H "Content-Type: application/json" \
  -d '{
    "audio_path": "/path/to/audio.wav",
    "threshold": 0.5
  }'
```

### NATS API

For service-to-service communication:

```python
from neuralux.messaging import MessageBusClient
from neuralux.config import NeuraluxConfig

bus = MessageBusClient(NeuraluxConfig())
await bus.connect()

# Speech-to-text
response = await bus.request("ai.audio.stt", {
    "audio_path": "/path/to/audio.wav",
    "language": "en"
}, timeout=60.0)

# Text-to-speech
response = await bus.request("ai.audio.tts", {
    "text": "Hello, world!",
    "speed": 1.0
}, timeout=30.0)

# Voice activity detection
response = await bus.request("ai.audio.vad", {
    "audio_path": "/path/to/audio.wav"
}, timeout=10.0)

# Service info
info = await bus.request("ai.audio.info", {}, timeout=5.0)
```

## Configuration

Configure the audio service via environment variables:

```bash
# Speech-to-Text
export AUDIO_STT_MODEL=medium            # tiny, base, small, medium, large
export AUDIO_STT_LANGUAGE=auto           # Language code or "auto"
export AUDIO_STT_DEVICE=auto             # cuda, cpu, or auto
export AUDIO_STT_COMPUTE_TYPE=auto       # int8, float16, float32, or auto

# Text-to-Speech
export AUDIO_TTS_MODEL=en_US-lessac-medium  # Voice model name
export AUDIO_TTS_SPEED=1.0               # Default speech speed

# Voice Activity Detection
export AUDIO_VAD_ENABLED=true            # Enable/disable VAD
export AUDIO_VAD_THRESHOLD=0.5           # Detection threshold (0.0-1.0)

# Audio settings
export AUDIO_SAMPLE_RATE=16000           # Sample rate for recording
export AUDIO_CHANNELS=1                  # 1=mono, 2=stereo

# Service
export AUDIO_SERVICE_PORT=8006           # HTTP port
```

Or create a `.env` file:

```bash
# Audio Service Configuration
AUDIO_STT_MODEL=base
AUDIO_STT_DEVICE=cuda
AUDIO_TTS_MODEL=en_US-lessac-medium
```

## Performance

### STT (Speech-to-Text)

| Model  | Size   | GPU Speed | CPU Speed | Accuracy |
|--------|--------|-----------|-----------|----------|
| tiny   | 40MB   | ~0.5s     | ~2s       | Basic    |
| base   | 140MB  | ~1s       | ~5s       | Good     |
| small  | 460MB  | ~2s       | ~10s      | Better   |
| medium | 1.5GB  | ~5s       | ~30s      | High     |
| large  | 3GB    | ~10s      | ~60s      | Best     |

*Tested on 10 seconds of audio, RTX 3090 / i7-10700K*

### TTS (Text-to-Speech)

- **Latency**: ~50-100ms for short phrases
- **Speed**: Real-time factor of ~0.1-0.2 (10-20x faster than real-time)
- **Memory**: ~100-200MB RAM

### VAD (Voice Activity Detection)

- **Latency**: ~10-20ms per second of audio
- **Accuracy**: >95% for clear speech

## Troubleshooting

### "PyAudio not installed"

**Ubuntu/Debian:**
```bash
sudo apt install -y portaudio19-dev
pip install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

### "No audio player found"

Install one of these:
```bash
sudo apt install -y alsa-utils  # For aplay
# OR
sudo apt install -y pulseaudio-utils  # For paplay
# OR
sudo apt install -y ffmpeg  # For ffplay
```

### "faster-whisper model not found"

Models download automatically on first use. Ensure you have internet connectivity and disk space:
```bash
mkdir -p models/audio/whisper
# Models will download to this directory automatically
```

### "Piper model not found"

Download Piper voice models manually:
```bash
mkdir -p models/audio/piper
cd models/audio/piper
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.json
```

### GPU Out of Memory

Use a smaller STT model or CPU mode:
```bash
export AUDIO_STT_MODEL=tiny
# OR
export AUDIO_STT_DEVICE=cpu
```

### Poor transcription quality

1. Use a larger model: `export AUDIO_STT_MODEL=medium`
2. Specify the language: `aish listen --language en`
3. Ensure clear audio input with minimal background noise
4. Use VAD to remove silence: `--vad-filter` (enabled by default)

### Microphone not working

Test your microphone:
```bash
arecord -d 5 test.wav  # Record 5 seconds
aplay test.wav         # Play back
```

Check available devices:
```python
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"{i}: {info['name']}")
```

## Examples

### Voice-controlled commands

```bash
# Record voice command and execute
aish listen | xargs aish ask --execute
```

### Create audio notes

```bash
# Record and save transcription
aish listen --duration 30 --output notes.txt
```

### Read text files aloud

```bash
# Read a file
cat document.txt | xargs aish speak
```

### Multi-language transcription

```bash
# French
aish listen --language fr

# Spanish
aish listen --language es

# Auto-detect
aish listen --language auto
```

## Architecture

```
┌─────────────────────────────────────────┐
│         Audio Service (Port 8006)        │
├─────────────────────────────────────────┤
│  • FastAPI REST API                     │
│  • NATS Message Bus Handler             │
│  • STT Backend (faster-whisper)         │
│  • TTS Backend (Piper)                  │
│  • VAD Backend (Silero)                 │
└─────────────────────────────────────────┘
         │                    │
    ┌────▼────┐         ┌────▼────┐
    │   aish  │         │  NATS   │
    │  CLI    │         │   Bus   │
    └─────────┘         └─────────┘
```

## Roadmap

### Planned Features (Phase 2B)

- [ ] Wake word detection ("Hey Neuralux")
- [ ] Continuous listening mode
- [ ] Speaker diarization (who's speaking)
- [ ] Real-time streaming transcription
- [ ] Voice commands integration with overlay
- [ ] Multi-language voice cloning (XTTS-v2)
- [ ] Audio file analysis (music, sound effects)

## Contributing

The audio service is part of the Neuralux project. See the main README for contribution guidelines.

## License

Apache 2.0 - See LICENSE file

---

**Need help?** Check the main documentation or open an issue on GitHub.

