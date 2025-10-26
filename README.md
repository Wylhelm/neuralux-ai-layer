# Neuralux AI Layer

An AI-powered operating system layer for Linux that provides intelligent assistance, automation, and insights at the system level.

## Overview

Neuralux AI Layer integrates advanced AI capabilities directly into your Linux system, offering:
- ✅ **Natural language command interface** - Talk to your system naturally
- ✅ **Semantic file search** - Find files by content, not just names
- ✅ **Intelligent command generation** - AI suggests safe, correct commands
- ✅ **System health monitoring** - Real-time metrics with anomaly detection
- ✅ **Voice interface** - Speech-to-text and text-to-speech
- ✅ **Image generation** - AI-powered image creation with Flux models
- ✅ **OCR and vision** - Extract text from images and screens
- 🚧 Gesture and advanced GUI interactions (Phase 2/3)
- ✅ **Privacy-first, local-first processing** - Your data stays on your machine

## Demo Video

[![Neuralux AI Layer Demo](https://img.youtube.com/vi/xFLJO7vTAoo/maxresdefault.jpg)](https://youtu.be/xFLJO7vTAoo?si=xhOXGHLA6vuEuQ4D)

Watch the demo video to see Neuralux AI Layer in action!

## Requirements

### Minimum Hardware
- **GPU**: NVIDIA GTX 1080 or AMD RX 6700 XT (8GB VRAM)
- **RAM**: 16GB
- **Storage**: 50GB free space
- **OS**: Ubuntu 24.04 LTS (Noble) or compatible

### Recommended Hardware
- **GPU**: NVIDIA RTX 3090 or better (24GB VRAM)
- **RAM**: 32GB+
- **Storage**: 100GB+ SSD

## Architecture

Neuralux uses a microservices architecture with:
- **Message Bus**: NATS.io for inter-service communication
- **AI Services**: LLM, Vision, Audio processing
- **System Integration**: File system intelligence, health monitoring, process management
- **User Interfaces**: CLI, GUI, Voice, Gesture

## Quick Start

### One-Command Installation

```bash
curl -fsSL https://raw.githubusercontent.com/Wylhelm/neuralux-ai-layer/main/install.sh | bash
```

Or manual installation:

```bash
# Clone the repository
git clone https://github.com/Wylhelm/neuralux-ai-layer
cd neuralux-ai-layer

# Start everything (infra + Python services)
make start-all

# Install Python dependencies
pip install -r requirements.txt
pip install -e packages/common/
pip install -e packages/cli/

# Download a model
mkdir -p models
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  -O models/llama-3.2-3b-instruct-q4_k_m.gguf

# Optional: start the GUI overlay in background (with tray)
make overlay
```

### First Commands

```bash
# Start the AI shell
aish

# Try natural language commands
> "show me large files in my downloads folder"
> "what's using the most CPU?"
> "find files about machine learning"

# Explain complex commands
> "/explain docker compose ps"

# Search files semantically
> "search files containing python code"
```

### Index Your Files

```bash
# Index your documents for semantic search
aish index ~/Documents
aish index ~/Projects

# Then search naturally
aish
> "find files about docker configuration"
> "locate documents about AI"
```

**Supported File Formats:**
- **Documents**: PDF, DOCX, ODT (LibreOffice Writer)
- **Spreadsheets**: XLSX, XLS, ODS (LibreOffice Calc), CSV
- **Code**: Python, JavaScript, Java, C/C++, Go, Rust, and more
- **Text**: Markdown, TXT, JSON, YAML, XML, HTML, CSS, SQL

### Overlay Assistant (GUI)

Install GTK bindings (Ubuntu/Debian):
```bash
sudo apt install -y python3-gi gir1.2-gtk-4.0 libgtk-4-1 libgtk-4-bin
```

Launch the overlay:
```bash
aish overlay                    # Start overlay (no hotkey)
aish overlay --hotkey           # Enable Ctrl+Space hotkey (X11 only)
aish overlay --hotkey --tray    # Enable both hotkey and tray (recommended)

# Control an existing instance (Wayland-friendly):
aish overlay --toggle   # Toggle visibility
aish overlay --show     # Show/focus
aish overlay --hide     # Hide
```

**Important:** The `--hotkey` flag is **required** to enable the global Ctrl+Space hotkey on X11. Without it, use the tray icon or control commands.

**Features:**
- 🎨 **Image Generation**: Click the paint button to generate images with AI (Flux models)
- 🎤 **Voice Input**: Use the microphone button for voice commands
- 📸 **OCR**: Extract text from screenshots or windows
- **Movable Window**: Drag the "≡ Neuralux ≡" header to reposition
- Press Esc to hide the overlay

On Wayland, bind a desktop shortcut to run `aish overlay --toggle`. Tray works if AppIndicator is available.

Troubleshooting (X11): If the overlay appears behind other windows, ensure you're on Xorg and try:
```bash
sudo apt install -y wmctrl
wmctrl -x -r com.neuralux.overlay -b add,above,sticky
```

#### Desktop integration and tray (optional)

Install AppIndicator support (Ubuntu/Debian) for the tray icon:
```bash
sudo apt install -y gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1
```

Create an application launcher via Makefile:
```bash
make desktop
```

Autostart on login (optional):
```bash
make autostart
```

Tip: On Wayland, use the launcher entry or bind a DE keyboard shortcut to run `aish overlay --toggle`.
You can also enable the tray by default by setting an environment variable:
```bash
export OVERLAY_ENABLE_TRAY=true
```

Customize tray name and icon (optional):
```bash
# App name shown to the desktop environment
export OVERLAY_APP_NAME="Neuralux"

# Use bundled icon (auto) or provide an absolute path or icon theme name
# Defaults to bundled icon if available
export OVERLAY_TRAY_ICON="$PWD/packages/overlay/assets/neuralux-tray.svg"

aish overlay --tray
```

### OCR and Overlay Actions

```bash
# CLI OCR
aish ocr --file /path/to/image.png
aish ocr --region 100,200,800,400
aish ocr --window

# Overlay OCR
# In overlay suggestions, pick "OCR active window" or type: /ocr window
# Then use buttons under the result: Copy, Summarize, Translate, Extract table, Continue chat, Start fresh
```

Contextual chat & session memory
- After OCR, click "Continue chat" to ask follow-ups with the OCR text as context.
- "Start fresh" clears the session. Sessions are shared across overlay and CLI via Redis (24h TTL).

### Image Generation

Generate images directly from the overlay using state-of-the-art Flux AI models:

```bash
# Launch overlay
aish overlay --hotkey --tray

# Click the 🎨 button or type a prompt
# Example: "a serene mountain landscape at sunset"
# Wait for generation with real-time progress
# Use Save/Copy buttons or continue chatting about the image
```

**Available Models:**
- **FLUX.1-schnell**: Ultra-fast 4-step generation (~5-10 seconds)
- **FLUX.1-dev**: High-quality detailed images
- **SDXL-Lightning**: Alternative fast model

**Features:**
- 8-bit quantization for efficient VRAM usage (~4GB)
- Real-time progress updates via SSE
- Configurable image size (512-1024px)
- Adjustable inference steps
- Save to PNG or copy to clipboard
- Continue conversation about generated images

**Configure settings** via Tray → Settings → Image Generation (model, size, steps)

See `IMAGE_GENERATION.md` for complete documentation.

### Monitor System Health

```bash
# View current system health
aish health

# Live monitoring dashboard (updates every 2 seconds)
aish health --watch

# Check service status
aish status
```

### Voice Interface

```bash
# Voice Assistant: Interactive conversation with voice I/O
aish assistant                       # Single turn conversation
aish assistant -c                    # Continuous conversation mode
aish assistant -d 10                 # 10 second recording per turn

# Speech-to-text: Record and transcribe
aish listen                          # Record 5 seconds
aish listen --duration 10            # Record 10 seconds
aish listen --file audio.wav         # Transcribe file
aish listen --language fr            # French transcription

# Text-to-speech: Convert text to audio
aish speak "Hello, world!"
aish speak "Faster speech" --speed 1.5
aish speak "Save audio" --output speech.wav
```

**Features:**
- **STT**: Powered by faster-whisper (Whisper optimized)
- **TTS**: Powered by Piper (fast neural TTS)
- **VAD**: Voice activity detection with Silero
- **Multi-language**: Auto-detect or specify language
- **Offline**: All processing happens locally

See `AUDIO.md` for complete voice interface documentation.

**Health Metrics:**
- **CPU**: Usage %, per-core stats, load averages
- **Memory**: RAM and swap usage with GB breakdown
- **Disk**: Usage for all partitions (auto-filters snap mounts)
- **Network**: Bytes sent/received, active connections
- **Processes**: Top 5 by CPU usage
- **Alerts**: Real-time warnings and critical alerts

**Alert Thresholds:**
- CPU: Warning @ 80%, Critical @ 95%
- Memory: Warning @ 85%, Critical @ 95%
- Disk: Warning @ 80%, Critical @ 90%

## Project Structure

```
neuralux-ai-layer/
├── services/           # Core microservices
│   ├── llm/           # Language model service
│   ├── filesystem/    # Semantic file search
│   ├── health/        # System health monitoring
│   ├── audio/         # Audio processing (STT/TTS) ✅
│   ├── vision/        # Computer vision (OCR + Image Gen) ✅
│   └── system/        # System intelligence (Phase 2)
├── packages/          # Installable packages
│   ├── cli/          # Command line interface (aish)
│   ├── common/       # Shared utilities
│   └── sdk/          # Plugin SDK (Phase 3)
├── infra/            # Infrastructure configs
│   ├── docker/       # Docker configurations
│   └── systemd/      # Service files
├── data/             # Service databases
└── docs/             # Documentation

```

## Development Status

**Current Phase**: 🚧 Phase 2A - Intelligence (In Progress)

### Phase 1 - Foundation ✅ Complete
- [x] Message bus infrastructure (NATS with JetStream)
- [x] LLM service (llama.cpp backend with GPU support)
- [x] CLI interface (aish - natural language commands)
- [x] Semantic file search (vector-based content search)
- [x] Docker Compose orchestration
- [x] Configuration management
- [x] One-command installation script
- [x] Comprehensive documentation

### Phase 2A - Intelligence ✅ Complete (16/16 tasks)
- [x] System health monitoring (CPU, memory, disk, network)
- [x] Real-time metrics collection with psutil
- [x] Time-series storage with DuckDB
- [x] Anomaly detection and alerting
- [x] NATS API endpoints for health queries
- [x] Beautiful terminal dashboard (`aish health`)
- [x] Live monitoring mode (`aish health --watch`)
- [x] System tray integration
- [x] Desktop packaging
- [x] GUI overlay (Alt+Space assistant)
- [x] Command palette with fuzzy search
- [x] Global hotkey listener (X11)
- [x] LLM integration in GUI
- [x] Screen context awareness (minimal)

### Phase 2B - Advanced Intelligence 🚧 In Progress (3/4 tasks)
- [x] Voice interface (STT/TTS) ✅
  - Speech-to-text with faster-whisper
  - Text-to-speech with Piper
  - Voice activity detection with Silero
  - CLI commands: `aish listen`, `aish speak`
- [x] Vision service (OCR + Image Generation) ✅ **NEW!**
  - OCR with PaddleOCR (CLI and overlay)
  - Image generation with Flux AI models (FLUX.1-schnell, FLUX.1-dev, SDXL-Lightning)
  - 8-bit quantization for VRAM efficiency
  - Real-time progress streaming via SSE
  - Overlay integration with 🎨 button
  - Quick actions: Save, Copy to clipboard, Continue chat
- [ ] Temporal intelligence (system history)
- [ ] Enhanced automation

### Additional Docs

- See `AUDIO.md` for voice interface guide and API documentation
- See `IMAGE_GENERATION.md` for image generation guide and troubleshooting
- See `OVERLAY.md` for overlay usage, Wayland guidance, tray, and troubleshooting
- See `API.md` for API endpoints and NATS subjects

### What's New (October 2025)

- **Image Generation** 🎨 **NEW!**
  - Generate images with Flux AI models directly in the overlay
  - Models: FLUX.1-schnell (4-step fast), FLUX.1-dev (quality), SDXL-Lightning
  - 8-bit quantization for efficient VRAM usage (~4GB vs ~20GB)
  - Real-time progress updates with SSE streaming
  - Save to PNG or copy to clipboard
  - Configure via Tray → Settings → Image Generation
  - Continue conversations about generated images
  
- Overlay assistant
  - **Movable window**: Drag the "≡ Neuralux ≡" header to reposition
  - Native Settings window (LLM/STT/Image Gen models, save defaults)
  - Native About dialog with Neuralux logo
  - Toast notifications and busy spinner for long operations
  - OCR region selection with mouse (via `slop`), hides overlay automatically
  - Better active window detection (xdotool/xprop fallback)
  - Conversation history with paging and session restore
  - New conversation button; refresh suggestions; expanded prompt suggestions
  - Slash command palette with fuzzy search when typing `/`
  - Web search in overlay fixed and improved
  
- Services
  - Vision service with image generation backend
  - LLM REST endpoint to hot-swap models (`POST /v1/model/load?model_name=`)
  - Audio STT endpoint to switch Whisper model (`POST /stt/model?name=`)
  - NATS reload events published during model swaps

Tip: Restart overlay after updates: `aish overlay --hotkey --tray`.

## License

Apache 2.0 - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

