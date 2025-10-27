# GPU Acceleration Guide

## Issue: Slow LLM Responses

**User reported**: "The responses are sometimes slow. Are we sure that we are using the GPU for the LLM and other services?"

## Investigation Results

### GPU Hardware
- ✅ **GPU**: NVIDIA GeForce RTX 3090 (24GB VRAM)
- ✅ **Driver**: 580.95.05
- ✅ **VRAM Usage**: 4.3GB / 24GB

### Service GPU Usage Status

| Service | GPU Usage | Status | Notes |
|---------|-----------|--------|-------|
| **Vision** | ✅ Yes | OK | 32GB RAM, properly using GPU |
| **Audio** | ✅ Yes | OK | Whisper STT on GPU |
| **LLM** | ❌ **NO** | **PROBLEM** | Running on CPU only! |
| Filesystem | ❌ Yes | Unexpected | Shouldn't need GPU |
| Health | N/A | OK | No GPU needed |

### Root Cause

The **LLM service is running on CPU instead of GPU** because `llama-cpp-python` was installed without CUDA support!

**Evidence:**
```bash
# LLM service memory usage
PID: 2404166
RAM: 8.8GB (model loaded in RAM, not VRAM)
GPU: Not visible in nvidia-smi (not using GPU)
```

**Why this happened:**
- `requirements.txt` has: `llama-cpp-python>=0.2.0`
- This installs the **pre-built wheel** which is **CPU-only**
- For GPU support, must compile with CUDA flags

## Performance Impact

### Current (CPU):
- ⏱️ Response time: 2-5 seconds
- 💻 Uses: 8.8GB RAM
- 🔥 CPU: 100% on multiple cores
- 📊 Speed: ~20-50 tokens/second

### Expected (GPU):
- ⚡ Response time: 0.3-1 seconds
- 🎮 Uses: 2-3GB VRAM
- 🔥 CPU: <10%
- 🚀 Speed: 100-300 tokens/second

**GPU should be 5-10x faster!**

## Solution

### Option 1: Automated Script (Recommended)

Run the provided script to automatically rebuild with CUDA:

```bash
cd /home/guillaume/NeuroTuxLayer
./enable-gpu-llm.sh
```

**What it does:**
1. Checks for NVIDIA GPU and CUDA toolkit
2. Stops the LLM service
3. Uninstalls CPU-only llama-cpp-python
4. Rebuilds with CUDA support (takes ~5-10 minutes)
5. Restarts the LLM service
6. Verifies GPU usage

### Option 2: Manual Installation

If you prefer to do it manually:

```bash
cd /home/guillaume/NeuroTuxLayer
source myenv/bin/activate

# Stop LLM service
./scripts/stop-services.sh

# Uninstall CPU version
pip uninstall -y llama-cpp-python

# Install with CUDA support
CMAKE_ARGS="-DGGML_CUDA=on" FORCE_CMAKE=1 pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir

# Restart services
./scripts/start-services.sh
```

### Prerequisites

Before rebuilding, ensure you have:

1. **NVIDIA Driver** (you have this ✅)
   ```bash
   nvidia-smi  # Should show your GPU
   ```

2. **CUDA Toolkit**
   ```bash
   nvcc --version  # Should show CUDA version
   ```
   
   If not installed:
   ```bash
   # Ubuntu/Debian
   sudo apt install nvidia-cuda-toolkit
   
   # Or download from: https://developer.nvidia.com/cuda-downloads
   ```

3. **Build tools**
   ```bash
   sudo apt install build-essential cmake
   ```

## Verification

After installation, verify GPU is being used:

### 1. Check GPU process list
```bash
nvidia-smi
```

You should see the Python LLM service process using GPU memory.

### 2. Check LLM logs
```bash
tail -f data/logs/llm-service.log
```

Look for messages like:
```
Loading model ... gpu_layers=-1
ggml_cuda_init: CUDA device found
offloading X layers to GPU
Model loaded successfully
```

### 3. Test response speed
```bash
aish
> what is docker?
```

Response should be near-instant (< 1 second).

### 4. Monitor GPU usage during query
```bash
# In one terminal
watch -n 0.5 nvidia-smi

# In another terminal
aish
> explain machine learning
```

You should see GPU utilization spike to 50-100% during inference.

## Expected Results

### Before (CPU-only):
```bash
$ nvidia-smi
# LLM service NOT visible

$ ps aux | grep 2404166
# RSS: 8852192 KB (8.8GB RAM)

$ aish
> hello
[2-3 seconds delay...]
Assistant: Hello! How can I help you?
```

### After (GPU):
```bash
$ nvidia-smi
# LLM service visible, using ~2-3GB VRAM

$ ps aux | grep [llm_pid]
# RSS: ~2000000 KB (2GB RAM - much less!)

$ aish
> hello
[instant response, <0.5 seconds]
Assistant: Hello! How can I help you?
```

## Other Services

### Vision Service
✅ Already using GPU correctly
- Shows in nvidia-smi
- Using 32GB RAM (model is large)
- GPU acceleration working

### Audio Service  
✅ Already using GPU correctly
- Whisper STT model on GPU
- Fast speech recognition
- No changes needed

### Filesystem Service
⚠️ Using GPU unexpectedly
- Semantic search might be using GPU embeddings
- This is fine, but monitor if it causes conflicts

## Troubleshooting

### Issue: CUDA not found
```
Error: CUDA toolkit not installed
```

**Solution:**
```bash
sudo apt install nvidia-cuda-toolkit
# or
sudo apt install nvidia-cuda-dev
```

### Issue: Compilation fails
```
error: nvcc not found
```

**Solution:**
```bash
# Find CUDA installation
find /usr -name nvcc 2>/dev/null

# Set CUDA path
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
```

### Issue: Service won't start after rebuild
```
Model not found error
```

**Solution:**
```bash
# Check model path
ls -lh /home/guillaume/NeuroTuxLayer/models/

# Restart service
cd /home/guillaume/NeuroTuxLayer
./scripts/stop-services.sh
./scripts/start-services.sh
```

### Issue: Still slow after rebuild
```
Responses still take 2-3 seconds
```

**Check:**
1. Verify GPU is actually being used: `nvidia-smi`
2. Check logs for GPU messages: `tail -f data/logs/llm-service.log`
3. Verify `n_gpu_layers=-1` in config
4. Try smaller model for testing: `llama-3.2-3b-instruct-q4_k_m.gguf`

## Performance Benchmarks

Expected performance on RTX 3090:

| Model | CPU (tokens/sec) | GPU (tokens/sec) | Speedup |
|-------|------------------|------------------|---------|
| Llama-3.2-3B-Q4 | 20-30 | 200-300 | ~10x |
| Mistral-7B-Q4 | 10-20 | 100-150 | ~7x |
| Llama-3-8B-Q4 | 8-15 | 80-120 | ~8x |

Response time for typical queries:
- **Greeting**: 0.1-0.3s (GPU) vs 1-2s (CPU)
- **Short answer**: 0.3-0.8s (GPU) vs 2-4s (CPU)
- **Long explanation**: 1-3s (GPU) vs 8-15s (CPU)

## Next Steps

1. **Run the enablement script**:
   ```bash
   ./enable-gpu-llm.sh
   ```

2. **Test the improvement**:
   ```bash
   aish
   > what is kubernetes?
   ```

3. **Monitor GPU usage**:
   ```bash
   nvidia-smi -l 1  # Update every second
   ```

4. **Enjoy 10x faster responses!** 🚀

## Files Modified

- Created: `enable-gpu-llm.sh` - Automated GPU enablement script
- Created: `GPU_ACCELERATION_GUIDE.md` - This documentation
- To modify: Virtual environment (`myenv/`) - Will rebuild llama-cpp-python

## Status

⚠️ **Action Required**: Run `./enable-gpu-llm.sh` to enable GPU acceleration for the LLM service.

Current state: LLM running on CPU (slow)
Target state: LLM running on GPU (10x faster)

Expected outcome: Near-instant responses for natural language queries! ⚡

