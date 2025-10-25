# Neuralux AI Layer

An AI-powered operating system layer for Linux that provides intelligent assistance, automation, and insights at the system level.

## Overview

Neuralux AI Layer integrates advanced AI capabilities directly into your Linux system, offering:
- Natural language command interface
- Semantic file search and understanding
- Intelligent system monitoring and automation
- Voice, gesture, and GUI interactions
- Privacy-first, local-first processing

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

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/neuralux-ai-layer
cd neuralux-ai-layer

# Start core services
docker compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Install CLI tool
pip install -e packages/cli/
```

### First Commands

```bash
# Start the AI shell
aish

# Try natural language commands
> "show me large files in my downloads folder"
> "what's using the most CPU?"
> "explain this error: permission denied /var/log"
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

**Current Phase**: Foundation (Phase 1)
- [x] Project structure
- [ ] Message bus infrastructure
- [ ] Basic LLM service
- [ ] CLI interface
- [ ] Semantic file search

## License

Apache 2.0 - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

