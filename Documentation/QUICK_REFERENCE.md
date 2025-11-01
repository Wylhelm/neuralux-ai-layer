# Neuralux Quick Reference

## 🚀 Quick Start Commands

### Start Everything
```bash
make start-all          # Start infra + all Python services (background)
aish                    # Use AI shell
```

### Check Status
```bash
make status             # Check all services
aish status            # Check from CLI
docker compose ps      # Docker services
```

### Stop Everything
```bash
make stop-all          # Stop services and infra
```

## 🧪 Testing Commands

```bash
./test-neuralux.sh           # Run full test suite
python3 demo-without-model.py  # Test infrastructure only
pytest tests/ -v             # Run Python unit tests
make test                    # Run all tests via Makefile
```

## 📦 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| NATS | `nats://localhost:4222` | Message bus |
| NATS Monitor | `http://localhost:8222` | NATS monitoring |
| Redis | `redis://localhost:6379` | Cache |
| Qdrant HTTP | `http://localhost:6333` | Vector DB |
| Qdrant gRPC | `localhost:6334` | Vector DB |
| LLM Service | `http://localhost:8000` | AI API |
| Vision Service | `http://localhost:8005` | OCR / vision API |

## 🔧 Common Tasks

### View Logs
```bash
docker compose logs -f              # All services
docker compose logs -f nats         # NATS only
tail -f llm-service.log            # LLM service (if backgrounded)
```

### Restart Services
```bash
make restart                        # Restart infrastructure
docker compose restart nats         # Restart specific service
```

### Clean Up
```bash
make clean                          # Clean Python cache
docker compose down -v              # Remove volumes (reset data)
```

## 🤖 aish CLI Commands

### Interactive Mode
```bash
aish                    # Start interactive shell
> "your command here"
> /explain ps aux
> /web how to check gpu utilization on linux
> /mode chat            # Natural answers mode
> /help
> /exit
```

### Single Command
```bash
aish ask "find large files"              # Get command only
aish ask "show disk usage" --execute     # Execute directly
aish explain "tar -xzf file.tar.gz"      # Explain command
aish web "ubuntu nvidia driver issue" --limit 5  # Web search with summaries
aish status                              # Check services
```

### Overlay
```bash
aish overlay                 # Launch GUI overlay (GTK4, no hotkey)
aish overlay --hotkey        # Enable Ctrl+Space hotkey (X11 only) - REQUIRED for hotkey
aish overlay --hotkey --tray # Enable both hotkey and tray (recommended)
aish overlay --toggle        # Toggle an existing overlay instance
aish overlay --show          # Show/focus existing overlay instance
aish overlay --hide          # Hide overlay instance
```

**Note:** You MUST use `--hotkey` to enable the Ctrl+Space hotkey. Press Esc to hide.

Shortcuts and tips:
- Tray → Settings: choose LLM/STT/Image Gen models, sizes, and steps
- 🎨 **Image Generation**: Click paint button, enter prompt, wait for generation
- Slash palette: type `/` to browse commands; `/web <query>` or "search the web for …" for web search
- OCR region select: `/ocr select` (install `slop`)
- Conversation: "Continue chat" uses last OCR/image as context; "Start fresh" clears memory
- **Movable window**: Drag the "≡ Neuralux ≡" header to reposition

See `OVERLAY.md` for Wayland tips, tray setup, and troubleshooting.

#### Overlay OCR and Actions
```bash
# CLI
aish ocr --file /path/to/image.png
aish ocr --region 100,200,800,400
aish ocr --window

# Overlay
# Select "OCR active window" in suggestions or type: /ocr window
# Then use buttons: Copy, Summarize, Translate, Extract table, Continue chat, Start fresh
```

Shared session memory (24h)
- Continue chat and Start fresh manage a Redis-backed session shared with CLI.
- Configure Redis URL in `packages/common/neuralux/config.py`.

### Voice Commands
```bash
# Voice Assistant (Interactive conversation)
aish assistant                       # Single turn conversation
aish assistant -c                    # Continuous conversation mode
aish assistant -d 10                 # 10 second recording per turn

# Speech-to-text
aish listen                          # Record 5 seconds and transcribe
aish listen --duration 10            # Record 10 seconds
aish listen --file audio.wav         # Transcribe file
aish listen --language fr            # Specify language

# Text-to-speech
aish speak "Hello, world!"
aish speak "Faster" --speed 1.5
aish speak "Save" --output audio.wav
```

See `AUDIO.md` for complete voice interface documentation.

Overlay voice, image generation & approvals:
- 🎤 Mic: single-turn voice capture (STT → LLM)
- 🔇/🔊 Speaker: toggle auto TTS of results
- 🎨 Image Gen: generate images with Flux AI models (Flux-schnell, Flux-dev, SDXL-Lightning)
  - Click button, enter prompt, view progress, Save/Copy result
  - Configure via Tray → Settings → Image Generation (model, size, steps)
- Approvals: actions (run command, open file/URL) require Approve/Cancel
- Web search by voice: say "search the web for <query>"

#### Tray and desktop integration (optional)
```bash
# Install AppIndicator support (Ubuntu/Debian)
sudo apt install -y gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1

# Create launcher via Makefile
make desktop

# Autostart on login (optional)
make autostart
```

Enable tray by default via env:
```bash
export OVERLAY_ENABLE_TRAY=true
```

Customize tray name and icon:
```bash
export OVERLAY_APP_NAME="Neuralux"
export OVERLAY_TRAY_ICON="$PWD/packages/overlay/assets/neuralux-tray.svg"
```

Wayland tip: bind a desktop shortcut to run:
```bash
aish overlay --toggle
```

## 📁 Important Files

### Configuration
- `.env` - Environment variables (create from .env.example)
- `docker-compose.yml` - Infrastructure services
- `packages/common/neuralux/config.py` - Python config

### Services
- `services/llm/service.py` - LLM service
- `services/llm/config.py` - LLM configuration

### Scripts
- `scripts/start-all.sh` - Start infra + services (bg)
- `scripts/stop-all.sh` - Stop services + infra
- `test-neuralux.sh` - Comprehensive tests
- `demo-without-model.py` - Infrastructure demo

### Documentation
- `README.md` - Project overview
- `GETTING_STARTED.md` - Full setup guide
- `QUICKSTART.md` - 5-minute start
- `ARCHITECTURE.md` - Technical details
- `AUDIO.md` - Voice interface guide
- `OVERLAY.md` - GUI overlay guide
- `API.md` - API reference
- `QUICK_REFERENCE.md` - This file (includes /web, /mode chat, image gen)
- `IMAGE_GENERATION.md` - Image generation guide
- `TEST_RESULTS.md` - Test report
- `plan.md` - Original project plan

## 🐛 Troubleshooting

### Services Won't Start
```bash
docker compose down      # Stop everything
docker compose up -d     # Start fresh
docker compose logs      # Check logs
```

### NATS Not Connecting
```bash
curl http://localhost:8222/varz  # Check if running
docker compose restart nats      # Restart NATS
```

### Python Package Issues
```bash
pip install -e packages/common/ --force-reinstall
pip install -e packages/cli/ --force-reinstall
```

### aish Not Found
```bash
export PATH="$HOME/.local/bin:$PATH"  # Add to PATH
pip install -e packages/cli/           # Reinstall
```

### Model Not Loading
```bash
# Check model exists
ls -lh models/

# Check model path in config
cat .env | grep LLM_DEFAULT_MODEL

# Try CPU mode
export LLM_GPU_LAYERS=0
```

## 🔐 Git Commands

### Push to GitHub
```bash
git status                    # Check changes
git add .                     # Stage all
git commit -m "message"       # Commit
git push -u origin main       # Push
```

### View History
```bash
git log --oneline             # View commits
git diff                      # View changes
```

## 📊 Monitoring

### Check Resource Usage
```bash
docker stats                           # Container resources
docker compose top                     # Processes
htop                                   # System resources
```

### Check Disk Space
```bash
docker system df                       # Docker disk usage
du -sh models/                        # Model size
du -sh ~/.cache/neuralux/             # Cache size
```

## 🔑 Key Directories

```
~/.config/neuralux/     # Configuration files
~/.cache/neuralux/      # Cache data
~/.local/share/neuralux/ # Application data
```

## 💡 Tips

1. **First Time Setup**: Run `./test-neuralux.sh` to verify everything
2. **Model Choice**: 3B for speed, 7B+ for quality
3. **CPU Mode**: Set `LLM_GPU_LAYERS=0` if no GPU
4. **Logs**: Use `docker compose logs -f` to debug issues
5. **Updates**: `git pull` then `make restart`

## 📞 Getting Help

```bash
aish --help             # CLI help
make help              # Makefile commands
docker compose --help  # Docker Compose help
pytest --help          # Test framework help
```

## 🎯 Next Steps

Based on your `plan.md`:

### Phase 1 (Current)
- ✅ Core infrastructure
- ✅ LLM service
- ✅ CLI tool
- ⏳ Semantic file search
- ⏳ Model management UI

### Phase 2 (Next)
- Vision service
- GUI overlay (Alt+Space)
- Audio service (STT/TTS)
- Temporal intelligence
- System monitoring

### Phase 3 (Future)
- Gesture recognition
- Developer tools
- Media generation
- Collaboration features
- Plugin system

---

**Quick Links**:
- GitHub: https://github.com/Wylhelm/neuralux-ai-layer
- Plan: `plan.md`
- Tests: `./test-neuralux.sh`
- Demo: `python3 demo-without-model.py`

