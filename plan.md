# AI Layer for Linux: Complete Implementation Plan

## Project Overview

**Name**: Neuralux AI Layer  
**Target Platform**: Ubuntu Noble (24.04 LTS) initially, expandable to other distributions  
**Minimum Requirements**: NVIDIA GTX 1080 or AMD RX 6700 XT (8GB VRAM)  
**Recommended**: NVIDIA RTX 3090 or better (24GB VRAM)  
**License**: Apache 2.0 with optional proprietary extensions

## 📊 Development Progress

**Last Updated**: October 26, 2025

### Overall Status: Phase 2A (MVP complete + desktop packaging)

| Phase | Status | Progress | Completion Date |
|-------|--------|----------|-----------------|
| Phase 1: Foundation | ✅ Complete | 8/8 (100%) | October 2025 |
| Phase 2A: Intelligence | 🚧 In Progress | MVP + Desktop packaging | In Progress |
| Phase 2B: Advanced Intelligence | 🚧 In Progress | 2/4 (50%) | In Progress |
| Phase 3: Advanced Features | ⏳ Planned | 0/5 (0%) | Future |
| Phase 4: Optimization | ⏳ Planned | 0/4 (0%) | Future |

### Recently Completed (October 2025)

**Phase 1 - Foundation** ✅
- Natural language CLI interface (`aish`)
- LLM service with llama.cpp + GPU support
- Semantic file search with Qdrant
- NATS message bus infrastructure
- Docker Compose orchestration
- One-command installation

**Phase 2A - Partial** ✅
- System health monitoring service (production ready)
  - Real-time CPU, memory, disk, network metrics
  - DuckDB time-series storage with 7/30/365 day retention
  - Anomaly detection with smart thresholds
  - Beautiful terminal dashboard (`aish health`)
  - Live monitoring mode
- Enhanced document support (ODT, ODS, XLSX, XLS, CSV)
- Improved semantic search (query extraction, better scoring)
- GUI overlay foundation (GTK4, theming, UI components)

### In Progress

- **GUI Overlay Assistant** (MVP complete + Tray + Desktop packaging)
  - Window and UI components ✅
  - Global hotkey listener (Alt+Space, X11) ✅
  - Fuzzy search (rapidfuzz fallback) ✅
  - LLM integration via NATS ✅
  - Minimal context awareness (active app) ✅
  - System tray integration ✅
  - Control flags (`--toggle`, `--show`, `--hide`) ✅
  - Makefile desktop targets (`make desktop`, `make autostart`) ✅
  - Voice controls (mic/speaker), auto TTS toggle, approvals for actions ✅
  - Web search in overlay (`/web` + voice “search the web …”), approval to open URLs ✅
  - OCR actions with buttons (Copy/Summarize/Translate/Extract), Continue chat/Start fresh ✅

### Next Priorities

1. Vision screen understanding (layouts, elements, objects)
2. Temporal intelligence (system history)
3. Streaming LLM + session persistence

For detailed progress, see: [PHASE2A_PROGRESS.md](PHASE2A_PROGRESS.md)

## Architecture Overview

### Core Design Principles
1. **Modular microservices architecture** with unified message bus
2. **Local-first processing** with optional cloud offload
3. **Privacy by design** with explicit user consent
4. **Progressive enhancement** based on hardware capabilities
5. **Distro-agnostic core** with Ubuntu-specific optimizations

### System Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  (CLI, GUI, Voice, Gesture, System Tray, IDE Plugins)       │
├─────────────────────────────────────────────────────────────┤
│                    API Gateway Layer                         │
│         (REST, gRPC, WebSocket, D-Bus interfaces)           │
├─────────────────────────────────────────────────────────────┤
│                  Orchestration Layer                         │
│  (Task Queue, Resource Scheduler, Permission Broker)         │
├─────────────────────────────────────────────────────────────┤
│                    AI Services Layer                         │
│  (LLM, Vision, STT, TTS, Generation, Analysis)              │
├─────────────────────────────────────────────────────────────┤
│                 System Integration Layer                     │
│  (OS Hooks, File System, Process Management, Hardware)       │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                                │
│  (Vector DB, Time Series DB, Knowledge Graph, Cache)         │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Message Bus Infrastructure

**Technology**: NATS.io with JetStream for persistence

```yaml
components:
  message_bus:
    type: NATS
    features:
      - Request/Reply for synchronous operations
      - Pub/Sub for event distribution
      - JetStream for message persistence
      - Subject-based routing for modularity
    subjects:
      - ai.llm.*
      - ai.vision.*
      - ai.audio.*
      - system.file.*
      - system.process.*
      - user.interaction.*
      - temporal.snapshot.*
```

### 2. AI Model Services

#### 2.1 Language Model Service
```yaml
service: llm_service
models:
  small:
    - Llama-3.2-3B-Instruct (4-bit quantized)
    - Phi-3.5-mini-instruct (4-bit)
  medium:
    - Mistral-7B-Instruct-v0.3
    - Llama-3.1-8B-Instruct
    - Qwen2.5-7B-Instruct
  large:
    - Mixtral-8x7B-Instruct (4-bit)
    - Llama-3.1-70B-Instruct (4-bit)
backends:
  - vLLM (primary, RTX 3090+)
  - llama.cpp (fallback, all GPUs)
  - TensorRT-LLM (optimization layer)
api: OpenAI-compatible REST + gRPC
```

#### 2.2 Vision Service
```yaml
service: vision_service
capabilities:
  ocr:
    - PaddleOCR (primary)
    - TesseractOCR (fallback)
    - RapidOCR (lightweight)
overlay:
  - actions:
      - ocr_active_window
      - quick_buttons: [copy, summarize, translate_en, translate_fr, extract_table]
      - session_controls: [start_chat, start_fresh]
  - session_memory:
      - backend: Redis
      - ttl: 24h
  screen_understanding:
    - LayoutLMv3 (document understanding)
    - OWLv2 (object detection)
    - CLIP (image-text matching)
  image_generation:
    - SDXL-Lightning (4-step)
    - FLUX.1-schnell (when VRAM allows)
  video_analysis:
    - WhisperX (audio extraction)
    - YOLOv8 (object tracking)
    - VideoLLaMA2 (when available)
```

#### 2.3 Audio Service
```yaml
service: audio_service
speech_to_text:
  - faster-whisper (primary)
  - whisper.cpp (CPU fallback)
  - wav2vec2 (lightweight)
text_to_speech:
  - Piper (primary, low latency)
  - XTTS-v2 (voice cloning)
  - Mimic3 (multilingual)
voice_activity_detection:
  - Silero VAD v5
wake_word:
  - OpenWakeWord
  - Porcupine (offline)
sound_generation:
  - AudioCraft (music/sfx)
  - Bark (speech synthesis)
```

### 3. System Integration Services

#### 3.1 File System Intelligence
```yaml
service: semantic_filesystem
components:
  content_indexer:
    - inotify watchers for real-time updates
    - Async content extraction pipeline
    - Multi-format parser (PDF, DOCX, code, etc.)
  vector_store:
    - Primary: Qdrant (embedded mode)
    - Fallback: SQLite with sqlite-vss
  relationship_graph:
    - Neo4j embedded or SQLite with graph extensions
  temporal_tracking:
    - Git-like content versioning
    - Metadata time series in DuckDB
features:
  - Semantic search across all content
  - Auto-tagging and categorization
  - Relationship mapping between files
  - Content-based deduplication
  - Privacy zones (excluded paths)
```

#### 3.2 Process and System Management
```yaml
service: system_intelligence
monitoring:
  - Process tree analysis via /proc
  - Resource usage via psutil
  - GPU metrics via nvidia-ml-py/rocm-smi
  - Network via netlink sockets
  - Thermal via lm-sensors
automation:
  - systemd unit management
  - Package management (apt/snap/flatpak)
  - Configuration management
  - Service health checks
predictive:
  - Resource usage forecasting
  - Failure prediction
  - Bottleneck identification
```

#### 3.3 Temporal Intelligence System
```yaml
service: temporal_intelligence
components:
  state_capture:
    interval: 5 minutes (configurable)
    captures:
      - Running processes and resource usage
      - Open windows and applications
      - System configuration changes
      - Network connections
      - File system changes
  storage:
    - TimescaleDB or DuckDB for time series
    - Deduplicated storage with rolling windows
    - Compressed snapshots for older data
  query_engine:
    - Natural language temporal queries
    - State comparison and diff generation
    - Correlation analysis
features:
  - "Show system state from 2 hours ago"
  - "What changed since this morning?"
  - "When did this problem start?"
  - Automatic correlation with system events
```

### 4. User Interface Components

#### 4.1 Command Line Interface
```yaml
component: ai_shell
location: /usr/local/bin/aish
features:
  - Natural language to command translation
  - Contextual awareness (pwd, git status, etc.)
  - History with semantic search
  - Pipeline generation
  - Error correction and explanation
  - Dry-run mode with diff preview
implementation:
  - Rust-based for performance
  - PTY for proper terminal emulation
  - Integration with existing shells (bash/zsh/fish)
```

#### 4.2 GUI Assistant Overlay
```yaml
component: desktop_assistant
activation: Alt+Space (configurable)
features:
  - Command palette with fuzzy search
  - Natural language actions
  - Screen context awareness
  - Visual feedback before actions
  - Workflow automation
implementation:
  - Wayland: Layer Shell protocol
  - X11: Override redirect window
  - GTK4 or Qt6 with OpenGL
  - AT-SPI2 for accessibility tree
```

#### 4.3 Voice Interface
```yaml
component: voice_assistant
wake_word: "Hey Neural" (configurable)
features:
  - Always-listening mode (optional)
  - Push-to-talk mode
  - Voice activity detection
  - Multi-language support
  - Speaker identification
implementation:
  - PipeWire for audio capture
  - GStreamer pipeline for processing
  - WebRTC echo cancellation
```

#### 4.4 Gesture Recognition
```yaml
component: gesture_control
requirements: Standard webcam
gestures:
  - Pinch: Minimize window
  - Swipe: Switch desktop
  - Palm: Pause media
  - Point: Focus element
implementation:
  - MediaPipe for hand tracking
  - OpenCV for image processing
  - Runs only when activated
```

### 5. Advanced Features

#### 5.1 Spatial Computing
```yaml
feature: spatial_intelligence
monitor_awareness:
  - RANDR/Wayland output detection
  - Logical monitor arrangement mapping
  - Window placement optimization
virtual_desktop_management:
  - Semantic workspace organization
  - Activity-based desktop switching
  - Automatic app grouping
implementation:
  - Integration with GNOME/KDE/Sway APIs
  - Custom window manager hints
```

#### 5.2 Developer Tools
```yaml
feature: dev_assistant
code_intelligence:
  - LSP integration for context
  - Dependency auto-resolution
  - Build optimization
  - Test generation
debugging:
  - Process attachment and analysis
  - Memory profiling
  - Performance regression detection
  - Bug reproduction from description
implementation:
  - VSCode/Neovim extensions
  - DAP (Debug Adapter Protocol) support
  - eBPF for system tracing
```

#### 5.3 Collaboration Features
```yaml
feature: collaboration
screen_sharing:
  - Automatic sensitive data blurring
  - Attention highlighting
  - Real-time transcription
meeting_assistant:
  - Speaker diarization
  - Action item extraction
  - Automatic minutes generation
pair_programming:
  - Code suggestion without interruption
  - Documentation lookup
  - Error detection
```

#### 5.4 Content Creation
```yaml
feature: media_generation
image:
  - Context-aware generation
  - In-app editing integration
  - Style transfer
video:
  - Scene detection and indexing
  - Automatic highlight reels
  - Smart transitions
audio:
  - Ambient music generation
  - Sound effect creation
  - Voice cloning (with consent)
```

### 6. Security and Privacy

#### 6.1 Security Framework
```yaml
security:
  permission_system:
    - Capability-based access control
    - Per-service AppArmor profiles
    - SELinux policies (when available)
  action_verification:
    - Human-readable diff preview
    - Sudo broker for elevated actions
    - Audit logging with explanations
  sandboxing:
    - Bubblewrap for plugin isolation
    - Firejail profiles
    - Container runtime for untrusted code
```

#### 6.2 Privacy Protection
```yaml
privacy:
  data_handling:
    - All processing local by default
    - Explicit opt-in for any cloud features
    - Automatic PII detection and redaction
  encryption:
    - At-rest: AES-256 via libsodium
    - In-transit: TLS 1.3 minimum
    - Key management via system keyring
  telemetry:
    - Opt-in only
    - Local analytics dashboard
    - No third-party trackers
```

### 7. Resource Management

#### 7.1 GPU Resource Scheduler
```yaml
scheduler:
  vram_management:
    - Dynamic model loading/unloading
    - Shared KV cache across models
    - Memory compaction
    - Batch inference optimization
  multi_gpu:
    - Model parallelism support
    - Round-robin scheduling
    - MIG support (A100/H100)
  profiles:
    - Battery Saver: CPU-only models
    - Balanced: 4-bit quantized models
    - Performance: Full precision models
    - Custom: User-defined limits
```

#### 7.2 Performance Optimization
```yaml
optimization:
  model_selection:
    - Automatic based on VRAM
    - Quality vs speed tradeoffs
    - Fallback chains
  acceleration:
    - TensorRT optimization
    - ONNX conversion
    - Flash Attention when available
    - Torch compilation
  caching:
    - Redis for hot data
    - Disk cache for models
    - Memory-mapped model loading
```

## Implementation Phases

### Phase 1: Foundation ✅ COMPLETE
```yaml
status: COMPLETE (October 2025)
goals:
  - ✅ Core message bus infrastructure (NATS with JetStream)
  - ✅ Basic LLM service with llama.cpp (GPU support)
  - ✅ CLI interface with natural language (aish)
  - ✅ Semantic file search (Qdrant vector store)
  - ✅ System command explanation
  - ✅ Document format support (PDF, DOCX, ODT, ODS, XLSX, CSV)
deliverables:
  - ✅ Docker compose for services
  - ✅ One-command installation script
  - ✅ Comprehensive documentation
  - ✅ CLI tool: 'aish' with multiple commands
  - ✅ Test suite (22/22 passing)
accomplishments:
  - Natural language command interface with context awareness
  - Semantic file search with content extraction
  - Real-time command execution with safety confirmations
  - Git-aware status display
  - Fuzzy file search across multiple formats
  - Beautiful Rich terminal UI
```

### Phase 2A: Intelligence (In Progress)
```yaml
status: IN PROGRESS (October 2025)
completed:
  - ✅ System health monitoring service
    - Real-time metrics (CPU, memory, disk, network)
    - DuckDB time-series storage
    - Anomaly detection with configurable thresholds
    - NATS API integration
    - Terminal dashboard (aish health)
    - Live monitoring mode (aish health --watch)
  - ✅ Enhanced document support (ODT, ODS, Excel)
  - ✅ Semantic search improvements (query extraction, scoring)
  - ✅ GUI overlay foundation (GTK4 window, theming)
  - ✅ GUI overlay assistant (Alt+Space, X11 hotkey)
    - ✅ Window and UI components
    - ✅ Global hotkey listener (X11)
    - ✅ Fuzzy search implementation
    - ✅ LLM integration
    - ✅ Minimal context awareness
    - ✅ Approvals for command execution and opening files/URLs
    - ✅ Detailed health view in overlay (CPU/Mem/Disk/Net/Top Procs/GPU) when available
    - ✅ Web search results with summaries and approval to open
pending:
  - ⏳ Temporal intelligence system
deliverables:
  - ✅ Health monitoring service (production ready)
  - ✅ Enhanced CLI with health dashboard
  - ✅ GUI overlay (MVP complete)
  - ✅ Desktop integration package (tray + .desktop)
docs:
  - OVERLAY.md (usage, Wayland guidance, tray, troubleshooting)
  - API.md (health REST endpoints and NATS subjects)
progress: MVP complete; docs polish and testing pending
```

### Phase 2B: Advanced Intelligence (In Progress)
```yaml
status: IN PROGRESS
goals:
  - Vision and screen understanding
  - Voice interface (STT/TTS)  
  - Temporal intelligence (system history)
  - Enhanced automation
deliverables:
  - Vision service skeleton with OCR endpoint and NATS stubs ✅
  - Vision service with OCR ✅
  - Voice assistant daemon (overlay controls implemented; wake word pending)
  - Temporal query system
  - Advanced automation rules
```

### Phase 3: Advanced Features (Months 7-9)
```yaml
goals:
  - Gesture recognition
  - Developer tool integration
  - Media generation capabilities
  - Collaboration features
  - Plugin system
deliverables:
  - IDE extensions
  - Plugin SDK and marketplace
  - Media generation UI
  - Collaboration tools
```

### Phase 4: Optimization and Polish (Months 10-12)
```yaml
goals:
  - Performance optimization
  - Multi-GPU support
  - Distributed processing
  - Federated learning
  - Production readiness
deliverables:
  - Performance benchmarks
  - Security audit results
  - Complete documentation
  - Installer with hardware detection
```

## Technical Stack

### Programming Languages
```yaml
core_services:
  - Rust: System services, CLI, performance-critical
  - Python: AI models, data processing, plugins
  - C++: GPU optimization, kernel modules
  - TypeScript: Web UI, VS Code extension
  - Go: Optional for some microservices
```

### Databases
```yaml
databases:
  vector_store: Qdrant (embedded)
  time_series: DuckDB or TimescaleDB
  document_store: SQLite with FTS5
  knowledge_graph: SQLite with graph extension
  cache: Redis or KeyDB
  configuration: etcd or Consul
```

### AI Frameworks
```yaml
frameworks:
  inference:
    - PyTorch (primary)
    - ONNX Runtime (optimization)
    - TensorRT (NVIDIA optimization)
    - llama.cpp (fallback)
  serving:
    - vLLM (LLM serving)
    - Triton Inference Server (optional)
    - Ray Serve (scaling)
```

### System Integration
```yaml
integration:
  desktop:
    - D-Bus for IPC
    - AT-SPI2 for accessibility
    - XDG portals for sandboxing
  audio:
    - PipeWire for audio routing
    - ALSA/PulseAudio fallback
  display:
    - Wayland protocols
    - X11 fallback
    - DRM for direct rendering
```

## Deployment and Distribution

### Packaging Strategy
```yaml
packaging:
  ubuntu_noble:
    - Meta-package: neuralux-ai-layer
    - Service packages: neuralux-*-service
    - PPA repository hosting
  universal:
    - Snap package (confined)
    - Flatpak for GUI components
    - AppImage for portable version
  source:
    - GitHub releases
    - Reproducible builds
    - Nix flake for NixOS
```

### Installation Process
```yaml
installer:
  stages:
    1. Hardware detection and validation
    2. Dependency resolution
    3. Model selection based on VRAM
    4. Service configuration
    5. Permission setup