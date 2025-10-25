# Neuralux AI Layer

An AI-powered operating system layer for Linux that provides intelligent assistance, automation, and insights at the system level.

## Overview

Neuralux AI Layer integrates advanced AI capabilities directly into your Linux system, offering:
- ✅ **Natural language command interface** - Talk to your system naturally
- ✅ **Semantic file search** - Find files by content, not just names
- ✅ **Intelligent command generation** - AI suggests safe, correct commands
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
- **System Integration**: File system intelligence, process management
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

## Project Structure

```
neuralux-ai-layer/
├── services/           # Core microservices
│   ├── llm/           # Language model service
│   ├── vision/        # Computer vision service
│   ├── audio/         # Audio processing service
│   ├── filesystem/    # Semantic file system
│   └── system/        # System intelligence
├── packages/          # Installable packages
│   ├── cli/          # Command line interface
│   ├── common/       # Shared utilities
│   └── sdk/          # Plugin SDK
├── infra/            # Infrastructure configs
│   ├── docker/       # Docker configurations
│   └── systemd/      # Service files
└── docs/             # Documentation

```

## Development Status

**Current Phase**: ✅ Phase 1 Complete!

### Completed Features
- [x] Message bus infrastructure (NATS with JetStream)
- [x] LLM service (llama.cpp backend with GPU support)
- [x] CLI interface (aish - natural language commands)
- [x] Semantic file search (vector-based content search)
- [x] Docker Compose orchestration
- [x] Configuration management
- [x] Test suite (22/22 passing)
- [x] One-command installation script
- [x] Comprehensive documentation

### Phase 2 (Next)
- [ ] Vision service (OCR, screen understanding)
- [ ] GUI overlay (Alt+Space assistant)
- [ ] Voice interface (STT/TTS)
- [ ] Temporal intelligence (system history)
- [ ] Enhanced automation

## License

Apache 2.0 - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

