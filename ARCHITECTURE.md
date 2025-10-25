# Neuralux Architecture

## Current Implementation Status

This document describes the current state of the Neuralux AI Layer implementation.

## What's Been Built (Phase 1 Foundation)

### ✅ Core Infrastructure

#### Message Bus (NATS)
- **Location**: `docker-compose.yml`
- **Features**:
  - JetStream for message persistence
  - Request/Reply for synchronous operations
  - Pub/Sub for event distribution
  - Health monitoring on port 8222

#### Vector Store (Qdrant)
- **Location**: `docker-compose.yml`
- **Features**:
  - Embedded mode for local vector storage
  - HTTP API (port 6333) and gRPC (port 6334)
  - Ready for semantic search implementation

#### Cache Layer (Redis)
- **Location**: `docker-compose.yml`
- **Features**:
  - LRU eviction policy
  - 1GB memory limit
  - Ready for model caching and session storage

### ✅ Common Package

**Location**: `packages/common/neuralux/`

#### Configuration Management (`config.py`)
- Pydantic-based configuration
- Environment variable support
- XDG directory compliance (`.config`, `.cache`, `.local/share`)
- Hardware profile support (battery_saver, balanced, performance)

#### Message Bus Client (`messaging.py`)
- Async NATS wrapper
- Request/Reply pattern
- Pub/Sub pattern
- Automatic reconnection
- Structured logging

#### Logging (`logger.py`)
- Structured logging with `structlog`
- JSON and console output modes
- Context-aware logging
- Service-specific loggers

### ✅ LLM Service

**Location**: `services/llm/`

#### Backend (`llm_backend.py`)
- llama.cpp integration
- GPU acceleration support
- Configurable model parameters
- Streaming generation
- Embeddings generation

#### REST API (`service.py`)
- FastAPI-based HTTP API
- OpenAI-compatible endpoints:
  - `POST /v1/chat/completions`
  - `POST /v1/embeddings`
  - `GET /v1/models`
- Streaming support
- Message bus integration

#### Features
- Automatic model loading
- Graceful fallback to CPU
- Memory-efficient quantization support
- Context-aware completions

### ✅ CLI Tool (aish)

**Location**: `packages/cli/aish/`

#### Features
- Interactive mode with rich UI
- Single-shot command mode
- Natural language to shell command translation
- Command explanation (`/explain`)
- Execution preview and confirmation
- Context awareness (cwd, git status)
- Service status checking

#### User Experience
- Syntax highlighting for commands
- Markdown rendering for explanations
- Colored output
- Progress indicators
- Safety confirmations

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     User Layer                          │
│                   aish CLI tool                         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────┐
│                 Message Bus (NATS)                      │
│            Request/Reply + Pub/Sub                      │
└────────┬──────────────────────────┬─────────────────────┘
         │                          │
┌────────┴──────────┐    ┌─────────┴──────────┐
│   LLM Service     │    │  Future Services   │
│   (llama.cpp)     │    │  - Vision          │
│   Port: 8000      │    │  - Audio           │
│                   │    │  - Filesystem      │
└────────┬──────────┘    └────────────────────┘
         │
┌────────┴──────────────────────────────────────┐
│         Storage & Cache Layer                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │ Qdrant  │  │  Redis  │  │  Local  │      │
│  │ Vector  │  │  Cache  │  │  Files  │      │
│  └─────────┘  └─────────┘  └─────────┘      │
└───────────────────────────────────────────────┘
```

## Component Communication

### Message Bus Subjects

Implemented:
- `ai.llm.request` - LLM completion requests
- `ai.llm.embed` - Embedding generation

Planned (from plan.md):
- `ai.llm.stream` - Streaming completions
- `ai.vision.*` - Vision service operations
- `ai.audio.*` - Audio service operations
- `system.file.*` - File system operations
- `system.process.*` - Process management
- `user.interaction.*` - User events
- `temporal.snapshot.*` - Temporal intelligence

### Data Flow Example: CLI Command

```
User Input: "show me large files"
        │
        ▼
    aish CLI
        │ (formats request)
        ▼
    NATS Request
    (ai.llm.request)
        │
        ▼
    LLM Service
        │ (generates command)
        ▼
    NATS Reply
        │
        ▼
    aish CLI
        │ (displays & confirms)
        ▼
    Shell Execution
```

## File Organization

```
NeuroTuxLayer/
├── docker-compose.yml          # Infrastructure services
├── requirements.txt            # Python dependencies
├── Makefile                    # Build & run commands
├── QUICKSTART.md              # Getting started guide
├── plan.md                     # Original project plan
├── ARCHITECTURE.md            # This file
│
├── packages/
│   ├── common/                # Shared utilities
│   │   └── neuralux/
│   │       ├── config.py      # Configuration
│   │       ├── messaging.py   # Message bus client
│   │       └── logger.py      # Logging setup
│   │
│   └── cli/                   # Command line interface
│       └── aish/
│           └── main.py        # CLI implementation
│
├── services/
│   └── llm/                   # Language model service
│       ├── config.py          # Service config
│       ├── models.py          # Data models
│       ├── llm_backend.py     # llama.cpp backend
│       └── service.py         # FastAPI service
│
├── scripts/
│   ├── start-services.sh      # Start all services
│   └── stop-services.sh       # Stop all services
│
└── tests/
    ├── test_config.py         # Config tests
    └── test_message_bus.py    # Message bus tests
```

## Next Steps (From Plan)

### Phase 1 Remaining
- [ ] Semantic file search implementation
- [ ] System command explanation enhancements
- [ ] Model management UI
- [ ] Ubuntu package (.deb)

### Phase 2 (Intelligence)
- [ ] Vision service (OCR, screen understanding)
- [ ] GUI overlay assistant (Alt+Space)
- [ ] Temporal intelligence system
- [ ] System health monitoring
- [ ] Voice interface (STT/TTS)

### Phase 3 (Advanced Features)
- [ ] Gesture recognition
- [ ] Developer tool integration
- [ ] Media generation
- [ ] Collaboration features
- [ ] Plugin system

### Phase 4 (Optimization)
- [ ] Performance optimization
- [ ] Multi-GPU support
- [ ] Distributed processing
- [ ] Production hardening

## Technology Choices

### Why NATS?
- Lightweight and fast
- Built-in persistence (JetStream)
- Multiple communication patterns
- Easy to scale

### Why llama.cpp?
- Broad model compatibility
- Efficient quantization
- GPU and CPU support
- No heavy frameworks required

### Why FastAPI?
- Modern async Python
- Automatic API documentation
- Type safety with Pydantic
- High performance

### Why Qdrant?
- Embedded mode for simplicity
- Production-ready
- Advanced filtering
- Good Python support

## Development Workflow

1. **Start Infrastructure**: `make start`
2. **Install Packages**: `make install`
3. **Run LLM Service**: `cd services/llm && python service.py`
4. **Use CLI**: `aish`

## Configuration

Configuration is environment-based with sensible defaults:

- **Development**: Uses `localhost` for all services
- **Production**: Override via environment variables
- **Custom**: Create `.env` file

Key configuration points:
- GPU acceleration: `LLM_GPU_LAYERS`
- Model selection: `LLM_DEFAULT_MODEL`
- Resource limits: `MAX_VRAM_GB`
- Privacy: `TELEMETRY_ENABLED`, `CLOUD_OFFLOAD_ENABLED`

## Testing

```bash
# Run all tests
make test

# Run specific test
pytest tests/test_config.py -v
```

Note: Message bus tests require running infrastructure.

## Logging

All services use structured logging:
- **Development**: Pretty console output
- **Production**: JSON for log aggregation
- **Levels**: DEBUG, INFO, WARNING, ERROR

View logs:
```bash
# Infrastructure logs
docker-compose logs -f

# Service logs
# (check terminal where service is running)
```

## Performance Considerations

### Current State
- **Model Loading**: ~5-10 seconds for 3B model
- **Inference**: ~10-50 tokens/second (GPU dependent)
- **Memory**: ~2-4GB VRAM for 4-bit quantized models

### Future Optimizations
- Model caching for faster restarts
- Batched inference for multiple requests
- KV cache sharing
- TensorRT optimization

## Security

### Implemented
- No telemetry by default
- Local-first processing
- Execution confirmation in CLI

### Planned
- AppArmor/SELinux profiles
- Capability-based permissions
- Action audit logging
- Sandboxed plugin execution

## Contributing

The foundation is now in place. Key areas for contribution:

1. **Additional Services**: Implement vision, audio, filesystem services
2. **UI Components**: Build the GUI overlay
3. **Models**: Add support for more model types
4. **Testing**: Expand test coverage
5. **Documentation**: Improve user guides

See the original `plan.md` for the complete vision.

