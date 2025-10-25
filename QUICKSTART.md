# Quick Start Guide

Get up and running with Neuralux AI Layer in 5 minutes!

## Prerequisites

- **Operating System**: Ubuntu 24.04 LTS (or compatible Linux)
- **GPU**: NVIDIA GTX 1080 or better (8GB+ VRAM)
- **RAM**: 16GB minimum
- **Software**: 
  - Docker & Docker Compose
  - Python 3.10+
  - Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/neuralux-ai-layer
cd neuralux-ai-layer
```

### 2. Start Core Services

Start the message bus, vector database, and cache:

```bash
docker compose up -d
```

Wait a moment for services to initialize:

```bash
# Check status (all should show as "Up")
docker compose ps
```

### 3. Install Python Packages

```bash
# Install dependencies
make install

# Or manually:
pip install -r requirements.txt
pip install -e packages/common/
pip install -e packages/cli/
### 4. (Optional) Install GTK Bindings for the Overlay

Ubuntu/Debian:
```bash
sudo apt install -y python3-gi gir1.2-gtk-4.0 libgtk-4-1 libgtk-4-bin
```

### 5. Start the LLM Service
```

### 4. Download an AI Model

You need a language model to use Neuralux. The default model is Llama-3.2-3B-Instruct (quantized, ~2GB):

```bash
# Create models directory
mkdir -p models

# Download the recommended model
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  -O models/llama-3.2-3b-instruct-q4_k_m.gguf
```

**Note**: This download is ~2GB and may take a few minutes.

### 5. Start the LLM Service

In a new terminal:

```bash
cd services/llm
python service.py
```

You should see:
```
INFO: Loading model...
INFO: Model loaded successfully
INFO: Connected to NATS
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 6. Try the AI Shell!

In another terminal:

```bash
aish
```

You'll see the interactive AI shell prompt. Try these commands:

```
aish> show me large files in my downloads folder
aish> what's using the most CPU?
aish> /explain ps aux | grep python
```

### Overlay Assistant

```bash
aish overlay
# X11 hotkey (Ctrl+Space by default):
aish overlay --hotkey
```

On Wayland, create a desktop shortcut that runs `aish overlay`.

## Verification

Check that everything is working:

```bash
# Check service status
aish status

# Expected output:
# ✓ Message bus: Connected
# ✓ LLM service: Running
```

## First Commands to Try

### File Operations
```
aish> find all python files in this directory
aish> show files larger than 100MB
aish> list files modified in the last hour
```

### System Information
```
aish> what's my disk usage?
aish> show running processes
aish> check memory usage
```

### Explain Commands
```
aish> /explain tar -xzf archive.tar.gz
aish> /explain docker ps -a
```

## Configuration

Create a configuration file (optional):

```bash
cp .env.example .env
nano .env
```

Key settings:
- `LLM_GPU_LAYERS=-1` - Use GPU (set to 0 for CPU only)
- `MAX_VRAM_GB=8` - Adjust based on your GPU
- `LOG_LEVEL=INFO` - Change to DEBUG for more details

## Troubleshooting

### Services won't start

```bash
# Check Docker
docker --version
docker compose version

# Restart services
docker compose down
docker compose up -d
```

### LLM service fails to start

**Model not found**:
- Make sure you downloaded the model to `./models/`
- Check the filename matches the config

**Out of memory**:
- Try CPU mode: Set `LLM_GPU_LAYERS=0` in your .env
- Or use a smaller model

### aish can't connect

Make sure services are running:
```bash
# Check NATS
curl http://localhost:8222/varz

# Check LLM service
curl http://localhost:8000/
```

## Next Steps

Now that you have the basics working:

1. **Explore more features**: Read the full README.md
2. **Customize your setup**: Edit the .env file
3. **Add more services**: Check the services/ directory
4. **Try different models**: Explore HuggingFace for more models

## Getting Help

- Check the documentation in `docs/`
- View logs: `docker compose logs -f`
- LLM service logs: Check the terminal where you ran `python service.py`

## Stopping Neuralux

```bash
# Stop the LLM service (Ctrl+C in its terminal)

# Stop infrastructure services
docker compose down
```

---

**Enjoy your AI-powered Linux experience!** 🚀

