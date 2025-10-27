#!/bin/bash
# Neuralux AI Layer - One-Command Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/Wylhelm/neuralux-ai-layer/main/install.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║          Neuralux AI Layer - Installation Script          ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}❌ Please do not run this script as root${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}❌ Cannot detect OS${NC}"
    exit 1
fi

echo -e "${BLUE}[1/8] System Check${NC}"
echo "  OS: $PRETTY_NAME"
echo "  User: $USER"
echo ""

# Check system requirements
echo -e "${BLUE}[2/8] Checking Requirements${NC}"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"
else
    echo -e "  ${RED}✗${NC} Python 3.10+ required"
    exit 1
fi

# Check Docker
if command -v docker &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Docker installed"
else
    echo -e "  ${YELLOW}⚠${NC} Docker not found, will provide instructions"
    INSTALL_DOCKER=true
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} Docker Compose v2 installed"
elif command -v docker-compose &> /dev/null; then
    echo -e "  ${YELLOW}⚠${NC} Old Docker Compose v1 found, recommend upgrade"
else
    echo -e "  ${YELLOW}⚠${NC} Docker Compose not found"
    INSTALL_DOCKER=true
fi

# Check for NVIDIA GPU
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    if [ -n "$GPU_NAME" ]; then
        echo -e "  ${GREEN}✓${NC} NVIDIA GPU detected: $GPU_NAME"
        HAS_GPU=true
        
        # Check for CUDA toolkit
        if [ -d "/usr/local/cuda" ] || [ -d "/usr/local/cuda-12.8" ] || command -v nvcc &> /dev/null; then
            echo -e "  ${GREEN}✓${NC} CUDA toolkit found"
            HAS_CUDA=true
        else
            echo -e "  ${YELLOW}⚠${NC} CUDA toolkit not found (GPU acceleration will be disabled)"
            HAS_CUDA=false
        fi
    fi
else
    echo -e "  ${YELLOW}ℹ${NC} No NVIDIA GPU detected (will use CPU)"
    HAS_GPU=false
fi

echo ""

# Install system dependencies
echo -e "${BLUE}[3/8] Installing System Dependencies${NC}"

if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    echo "  Installing build tools and libraries..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        build-essential \
        cmake \
        pkg-config \
        python3-dev \
        python3-pip \
        python3-venv \
        libdbus-1-dev \
        libglib2.0-dev \
        libgomp1 \
        libomp-dev \
        git \
        wget \
        curl
    echo -e "  ${GREEN}✓${NC} System dependencies installed"
else
    echo -e "  ${YELLOW}⚠${NC} Unsupported OS, manual installation required"
    echo "  Required: build-essential, cmake, pkg-config, python3-dev, libdbus-1-dev, libglib2.0-dev"
fi

echo ""

# Clone or update repository
echo -e "${BLUE}[4/8] Getting Neuralux${NC}"

if [ -d "neuralux-ai-layer" ]; then
    echo "  Directory exists, updating..."
    cd neuralux-ai-layer
    git pull
else
    echo "  Cloning repository..."
    git clone https://github.com/Wylhelm/neuralux-ai-layer.git
    cd neuralux-ai-layer
fi

echo -e "  ${GREEN}✓${NC} Code ready"
echo ""

# Create Python virtual environment
echo -e "${BLUE}[5/8] Setting Up Python Environment${NC}"

if [ ! -d "venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "  Installing Python packages..."

# Install llama-cpp-python with GPU support if available
if [ "$HAS_GPU" = true ] && [ "$HAS_CUDA" = true ]; then
    echo "  Installing llama-cpp-python with CUDA support..."
    
    # Find CUDA installation
    if [ -d "/usr/local/cuda-12.8" ]; then
        export CUDA_HOME=/usr/local/cuda-12.8
    elif [ -d "/usr/local/cuda" ]; then
        export CUDA_HOME=/usr/local/cuda
    fi
    
    export PATH=$CUDA_HOME/bin:$PATH
    export CMAKE_ARGS="-DGGML_CUDA=on"
    export FORCE_CMAKE=1
    
    pip install llama-cpp-python --upgrade --no-cache-dir -q
    echo -e "  ${GREEN}✓${NC} llama-cpp-python installed with GPU support"
else
    echo "  Installing llama-cpp-python (CPU-only)..."
    CMAKE_ARGS="-DGGML_BLAS=OFF -DGGML_OPENMP=OFF" pip install llama-cpp-python --no-cache-dir -q
    echo -e "  ${YELLOW}ℹ${NC} llama-cpp-python installed (CPU-only)"
fi

# Install remaining packages
pip install -r requirements.txt -q

# Install neuralux packages
pip install -e packages/common/ -q
pip install -e packages/cli/ -q

echo -e "  ${GREEN}✓${NC} Python environment ready"
echo ""

# Start infrastructure services
echo -e "${BLUE}[6/8] Starting Infrastructure Services${NC}"

if [ "$INSTALL_DOCKER" = true ]; then
    echo -e "  ${YELLOW}⚠${NC} Docker not installed. Please install Docker first:"
    echo "    https://docs.docker.com/engine/install/"
    echo ""
    echo "  Skipping service startup..."
else
    echo "  Starting NATS, Redis, and Qdrant..."
    docker compose up -d
    sleep 5
    
    if docker compose ps | grep -q "Up"; then
        echo -e "  ${GREEN}✓${NC} Infrastructure services running"
    else
        echo -e "  ${YELLOW}⚠${NC} Services may not be fully ready yet"
    fi
fi

echo ""

# Download model (optional)
echo -e "${BLUE}[7/8] AI Model Setup${NC}"

if [ -f "models/llama-3.2-3b-instruct-q4_k_m.gguf" ]; then
    echo -e "  ${GREEN}✓${NC} Model already downloaded"
else
    echo "  Model not found. Download options:"
    echo ""
    echo "  Option 1: Recommended model (~2GB):"
    echo "    mkdir -p models"
    echo "    wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \\"
    echo "      -O models/llama-3.2-3b-instruct-q4_k_m.gguf"
    echo ""
    echo "  The installer will continue. Download a model later to use AI features."
fi

echo ""

# Test installation
echo -e "${BLUE}[8/8] Testing Installation${NC}"

if command -v aish &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} aish command available"
    
    # Test service connectivity
    if [ "$INSTALL_DOCKER" != true ]; then
        if python3 -c "from neuralux.messaging import MessageBusClient; import asyncio; asyncio.run(MessageBusClient().connect())" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Message bus connection working"
        else
            echo -e "  ${YELLOW}⚠${NC} Message bus not yet ready (may need a moment)"
        fi
    fi
else
    echo -e "  ${RED}✗${NC} aish not found in PATH"
    echo "  Add to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║              Installation Complete! 🎉                     ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Show GPU status
if [ "$HAS_GPU" = true ] && [ "$HAS_CUDA" = true ]; then
    echo -e "${GREEN}✓ GPU Acceleration: Enabled${NC}"
    echo "  LLM will use GPU for 10x faster responses"
    echo ""
elif [ "$HAS_GPU" = true ] && [ "$HAS_CUDA" != true ]; then
    echo -e "${YELLOW}⚠ GPU Detected but CUDA Not Installed${NC}"
    echo ""
    echo "  Install CUDA toolkit for GPU acceleration:"
    echo "  sudo apt install nvidia-cuda-toolkit build-essential cmake"
    echo ""
    echo "  Then rebuild: ./enable-gpu-llm.sh"
    echo ""
fi

if [ "$INSTALL_DOCKER" = true ]; then
    echo -e "${YELLOW}⚠ Docker Installation Required${NC}"
    echo ""
    echo "Install Docker to use Neuralux:"
    echo "  Ubuntu: https://docs.docker.com/engine/install/ubuntu/"
    echo ""
    echo "Then run: docker compose up -d"
    echo ""
fi

echo "Next steps:"
echo ""
echo "1. Activate the environment:"
echo "   source venv/bin/activate"
echo ""

if [ ! -f "models/llama-3.2-3b-instruct-q4_k_m.gguf" ]; then
    echo "2. Download a model (required for AI features):"
    echo "   mkdir -p models && wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf -O models/llama-3.2-3b-instruct-q4_k_m.gguf"
    echo ""
    echo "3. Start the LLM service (after downloading model):"
    echo "   cd services/llm && python service.py &"
    echo ""
    echo "4. Use the AI shell:"
else
    echo "2. Start the LLM service:"
    echo "   cd services/llm && python service.py &"
    echo ""
    echo "3. Use the AI shell:"
fi
echo "   aish"
echo ""
echo "For help: aish --help"
echo "Documentation: https://github.com/Wylhelm/neuralux-ai-layer"
echo ""
echo "Enjoy your AI-powered Linux experience! 🚀"

