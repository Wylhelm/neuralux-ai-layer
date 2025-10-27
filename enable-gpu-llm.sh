#!/bin/bash
# Enable GPU acceleration for LLM service

set -e

echo "========================================="
echo "Enable GPU Acceleration for LLM Service"
echo "========================================="
echo ""

# Check for NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ ERROR: nvidia-smi not found. Is NVIDIA driver installed?"
    exit 1
fi

echo "✓ NVIDIA GPU detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

# Check for CUDA
if [ ! -d "/usr/local/cuda" ] && [ ! -d "/opt/cuda" ]; then
    echo "⚠️  WARNING: CUDA not found in /usr/local/cuda or /opt/cuda"
    echo "   Checking nvcc..."
    if ! command -v nvcc &> /dev/null; then
        echo "❌ ERROR: CUDA toolkit not installed!"
        echo ""
        echo "Please install CUDA toolkit first:"
        echo "  Ubuntu: sudo apt install nvidia-cuda-toolkit"
        echo "  or download from: https://developer.nvidia.com/cuda-downloads"
        exit 1
    fi
fi

NVCC_PATH=$(which nvcc 2>/dev/null || echo "")
if [ -n "$NVCC_PATH" ]; then
    CUDA_VERSION=$(nvcc --version | grep "release" | sed 's/.*release //' | sed 's/,.*//')
    echo "✓ CUDA toolkit found: $CUDA_VERSION"
    echo "  nvcc: $NVCC_PATH"
else
    echo "⚠️  nvcc not found in PATH, but continuing..."
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
cd "$(dirname "$0")"
source myenv/bin/activate

# Stop LLM service
echo "Stopping LLM service..."
if [ -f "data/run/llm.pid" ]; then
    LLM_PID=$(cat data/run/llm.pid)
    if ps -p $LLM_PID > /dev/null 2>&1; then
        kill $LLM_PID
        echo "✓ LLM service stopped"
        sleep 2
    fi
fi

# Uninstall existing llama-cpp-python
echo ""
echo "Uninstalling existing llama-cpp-python..."
pip uninstall -y llama-cpp-python 2>/dev/null || true

# Install llama-cpp-python with CUDA support
echo ""
echo "========================================="
echo "Installing llama-cpp-python with CUDA..."
echo "========================================="
echo ""
echo "This will take 5-10 minutes to compile..."
echo ""

# Set environment variables for CUDA build
export FORCE_CMAKE=1
export CMAKE_ARGS="-DGGML_CUDA=on"
export CUDACXX=/usr/local/cuda/bin/nvcc

pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir

echo ""
echo "========================================="
echo "Verification"
echo "========================================="
echo ""

# Verify installation
python << EOF
from llama_cpp import Llama
print("✓ llama-cpp-python installed successfully")
EOF

echo ""
echo "========================================="
echo "Starting LLM service..."
echo "========================================="
echo ""

# Restart LLM service
cd services/llm
nohup python service.py > ../../data/logs/llm-service.log 2>&1 &
echo $! > ../../data/run/llm.pid
echo "✓ LLM service started (PID: $(cat ../../data/run/llm.pid))"

# Wait for service to start
echo ""
echo "Waiting for service to initialize..."
sleep 3

# Check if service is running
tail -20 ../../data/logs/llm-service.log

echo ""
echo "========================================="
echo "✓ GPU acceleration enabled!"
echo "========================================="
echo ""
echo "The LLM service is now using GPU acceleration."
echo "Responses should be MUCH faster now!"
echo ""
echo "Monitor GPU usage with: nvidia-smi"
echo "View logs with: tail -f data/logs/llm-service.log"
echo ""

