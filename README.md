# Neuralux AI Layer

An AI-powered operating system layer for Linux that provides intelligent assistance, automation, and insights at the system level.

## Overview

Neuralux AI Layer integrates advanced AI capabilities directly into your Linux system, offering:
- ✅ **Natural language command interface** - Talk to your system naturally
- ✅ **Semantic file search** - Find files by content, not just names
- ✅ **Intelligent command generation** - AI suggests safe, correct commands
- ✅ **System health monitoring** - Real-time metrics with anomaly detection
- 🚧 Voice, gesture, and GUI interactions (Phase 2)
- ✅ **Privacy-first, local-first processing** - Your data stays on your machine

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

# Start core services
docker compose up -d

# Install Python dependencies
pip install -r requirements.txt
pip install -e packages/common/
pip install -e packages/cli/

# Download a model
mkdir -p models
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  -O models/llama-3.2-3b-instruct-q4_k_m.gguf

# Start services
cd services/llm && python service.py &
cd services/filesystem && python service.py &
cd services/health && python service.py &
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
aish overlay
# X11 hotkey (Alt+Space by default):
aish overlay --hotkey
# Tray icon (quick toggle from system tray):
aish overlay --tray
```

On Wayland, bind a desktop shortcut to run `aish overlay`. Tray works if AppIndicator is available.
Press Esc to hide the overlay.

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

Create an application launcher:
```bash
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/neuralux-overlay.desktop << 'EOF'
[Desktop Entry]
Name=Neuralux Overlay
Comment=Open the Neuralux assistant overlay
Exec=aish overlay
Terminal=false
Type=Application
Icon=utilities-terminal
Categories=Utility;
StartupNotify=false
EOF
```

Autostart on login (optional):
```bash
mkdir -p ~/.config/autostart
cp ~/.local/share/applications/neuralux-overlay.desktop ~/.config/autostart/
```

Tip: On Wayland, use the launcher entry or bind a DE keyboard shortcut to run `aish overlay`.
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

### Monitor System Health

```bash
# View current system health
aish health

# Live monitoring dashboard (updates every 2 seconds)
aish health --watch

# Check service status
aish status
```

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
│   ├── vision/        # Computer vision (Phase 2)
│   ├── audio/         # Audio processing (Phase 2)
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

### Phase 2A - Intelligence 🚧 In Progress (14/16 tasks)
- [x] System health monitoring (CPU, memory, disk, network)
- [x] Real-time metrics collection with psutil
- [x] Time-series storage with DuckDB
- [x] Anomaly detection and alerting
- [x] NATS API endpoints for health queries
- [x] Beautiful terminal dashboard (`aish health`)
- [x] Live monitoring mode (`aish health --watch`)
- [x] System tray integration
- [ ] Desktop packaging
- [x] GUI overlay (Alt+Space assistant)
- [x] Command palette with fuzzy search
- [x] Global hotkey listener (X11)
- [x] LLM integration in GUI
- [x] Screen context awareness (minimal)
- [ ] Temporal intelligence (system history)
- [ ] Documentation polish and user testing

### Phase 2B - Advanced Intelligence (Future)
- [ ] Vision service (OCR, screen understanding)
- [ ] Voice interface (STT/TTS)
- [ ] Enhanced automation

## License

Apache 2.0 - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

