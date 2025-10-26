# Getting Started with Neuralux AI Layer

## 🎉 Welcome!

You now have a working foundation for the Neuralux AI Layer! This guide will help you get everything running.

## What You Have

✅ **Core Infrastructure**
- NATS message bus for service communication
- Redis cache for fast data access
- Qdrant vector database for semantic search
- Docker Compose orchestration

✅ **LLM Service**
- llama.cpp backend for model inference
- OpenAI-compatible REST API
- Message bus integration
- GPU acceleration support

✅ **AI Shell (aish)**
- Natural language command interface
- Interactive and single-shot modes
- Command explanation
- Execution safety checks

✅ **Common Libraries**
- Configuration management
- Message bus client
- Structured logging

## Quick Setup (3 Steps)

### Step 1: Start Infrastructure

```bash
# Start NATS, Redis, and Qdrant
docker compose up -d

# Verify services are running
docker compose ps
```

All three services should show "Up" status.

### Step 2: Download a Model

You need a language model. Here's the recommended one (2GB):

```bash
# Create models directory
mkdir -p models

# Download Llama-3.2-3B-Instruct (quantized)
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  -O models/llama-3.2-3b-instruct-q4_k_m.gguf
```

**Alternative models:**
- Smaller (1.5GB): Phi-3.5-mini
- Larger (5GB): Mistral-7B
- More powerful (if you have 24GB+ VRAM): Mixtral-8x7B

All models should be in GGUF format from HuggingFace.

### Step 3: Install Python Packages

```bash
# Install all dependencies
make install

# Or manually:
pip install -r requirements.txt
pip install -e packages/common/
pip install -e packages/cli/
```

## Running Neuralux

### Option A: One command (infra + services)

```bash
# Start infra and all Python services in background
make start-all

# Optional: start the GUI overlay in background (with tray)
make overlay

# Use the AI shell
aish
```

### Option B: Manual

```bash
# Terminal 1: Start infrastructure
./scripts/start-services.sh

# Terminal 2: Start LLM service
cd services/llm
python service.py

# Terminal 3: Use the AI shell
aish
```

### Overlay Assistant and Desktop Integration (Optional)

Install GTK bindings (Ubuntu/Debian):
```bash
sudo apt install -y python3-gi gir1.2-gtk-4.0 libgtk-4-1 libgtk-4-bin
```

Launch/control the overlay:
```bash
aish overlay                 # Launch overlay (GTK4)
aish overlay --hotkey        # X11 hotkey (Alt+Space or Ctrl+Space)
aish overlay --tray          # System tray icon
# Control an existing instance (Wayland-friendly bindings):
aish overlay --toggle        # Toggle
aish overlay --show          # Show/focus
aish overlay --hide          # Hide
```

On Wayland, bind a desktop shortcut to run `aish overlay --toggle`.

Install AppIndicator support for tray/desktop (Ubuntu/Debian):
```bash
sudo apt install -y gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1
```

Create a launcher via Makefile and enable autostart (optional):
```bash
make desktop      # Install launcher
make autostart    # Autostart on login
```

## Your First Commands

Once everything is running, try these:

### Interactive Mode

```bash
aish
```

Then type:
```
> show me large files in my home directory
> what processes are using the most memory?
> /explain tar -xzf archive.tar.gz
> /exit
```

### Single Command Mode

```bash
# Get a command
aish ask "find all python files modified today"

# Execute directly (be careful!)
aish ask "show disk usage" --execute

# Explain something
aish explain "ps aux | grep python"

# Check status
aish status
```

## Troubleshooting

### "Failed to connect to message bus"

**Solution:**
```bash
# Check if NATS is running
curl http://localhost:8222/varz

# If not, start infrastructure
docker compose up -d
```

### "Model not found"

**Solution:**
```bash
# Check models directory
ls -lh models/

# Download the model (see Step 2 above)
```

### "Request timeout"

This usually means the LLM service is still loading the model (takes 5-10 seconds).

**Solution:**
- Wait a few more seconds
- Check LLM service logs in its terminal
- Verify the model file is correct

### Out of Memory

**For GPU:**
```bash
# Use CPU instead
export LLM_GPU_LAYERS=0
cd services/llm && python service.py
```

**For RAM:**
- Download a smaller model
- Close other applications
- Use the 3B model instead of 7B+

### Docker Issues

```bash
# Restart everything
docker compose down
docker compose up -d

# Check logs
docker compose logs -f
```

## Configuration

Create a `.env` file to customize:

```bash
# Copy example (if it exists) or create new
cat > .env << 'EOF'
# LLM Configuration
LLM_DEFAULT_MODEL=llama-3.2-3b-instruct-q4_k_m.gguf
LLM_GPU_LAYERS=-1  # -1=auto, 0=CPU only, >0=specific number of layers
LLM_MAX_CONTEXT=8192

# Resource Management  
MAX_VRAM_GB=8
PROFILE=balanced  # battery_saver, balanced, or performance

# Privacy
TELEMETRY_ENABLED=false
CLOUD_OFFLOAD_ENABLED=false

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
EOF
```

## Testing Your Setup

Run the test suite:

```bash
# Make sure infrastructure is running
make start

# Run tests
make test

# Or with pytest directly
pytest tests/ -v
```

## What to Try Next

### 1. Explore Different Commands

Try asking aish to:
- Manage files: "backup all my documents"
- Monitor system: "what's my CPU temperature?"
- Work with git: "show uncommitted changes"
- Process data: "count lines in all python files"

### 2. Understand How It Works

Read `ARCHITECTURE.md` to learn about:
- How services communicate
- The message bus pattern
- Data flow
- Component organization

### 3. Extend Neuralux

Pick a feature from `plan.md` Phase 2:
- **Vision Service**: OCR and screen understanding
- **Audio Service**: Speech-to-text, text-to-speech
- **Temporal Intelligence**: System state tracking
- **GUI Overlay**: Desktop assistant (Alt+Space)

### 4. Customize Your Models

Try different models for different tasks:
- Fast responses: Use 3B models
- Better quality: Use 7B models  
- Specialized: Use fine-tuned models

## Architecture Overview

```
┌──────────────────┐
│   aish (CLI)     │  ← You interact here
└────────┬─────────┘
         │
         ▼
┌────────────────────┐
│   NATS Message     │  ← Services communicate
│      Bus           │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│   LLM Service      │  ← AI model runs here
│   (llama.cpp)      │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Qdrant + Redis    │  ← Data stored here
└────────────────────┘
```

## Performance Tips

### Faster Inference
- Use GPU: Keep `LLM_GPU_LAYERS=-1`
- Smaller models: 3B instead of 7B
- Quantization: Q4_K_M is a good balance

### Lower Memory Usage
- CPU mode: `LLM_GPU_LAYERS=0`
- More aggressive quantization: Try Q3 or Q2 models
- Reduce context: `LLM_MAX_CONTEXT=4096`

### Better Quality
- Larger models: Use 7B or 13B
- Less quantization: Q8 or Q6_K
- Adjust temperature: Lower (0.3) for factual, higher (0.8) for creative

## Getting Help

### Documentation
- `README.md` - Project overview
- `QUICKSTART.md` - Fast setup guide (this file)
- `ARCHITECTURE.md` - Technical details
- `plan.md` - Full project vision

### Logs
```bash
# Infrastructure logs
docker compose logs -f

# LLM service logs
# Check the terminal where you ran python service.py

# Enable debug mode
export LOG_LEVEL=DEBUG
cd services/llm && python service.py
```

### Common Issues
1. **Services not starting**: Check Docker is running
2. **Model errors**: Verify file path and format (must be GGUF)
3. **Slow responses**: Wait for model to load (first request)
4. **Connection errors**: Ensure all services are up

## Stopping Neuralux

```bash
# Stop everything
make stop

# Or manually:
# 1. Ctrl+C in the LLM service terminal
# 2. docker compose down
```

## Development Mode

If you want to modify Neuralux:

```bash
# Install dev dependencies
make install-dev

# Format code
make format

# Run linter
make lint

# Run tests
make test
```

## Next Steps

You're ready to go! Here's what to do next:

1. ✅ **Use it**: Try aish with your daily tasks
2. 📖 **Learn**: Read ARCHITECTURE.md to understand the system
3. 🔧 **Extend**: Pick a feature from plan.md to implement
4. 🤝 **Contribute**: Share your improvements

---

**Enjoy your AI-powered Linux experience!** 🚀

Questions? Check the docs or open an issue on GitHub.

