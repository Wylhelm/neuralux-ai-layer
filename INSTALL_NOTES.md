# Installation Notes

## System Dependencies Required

### For dbus-python (Desktop Integration)
```bash
sudo apt-get install libdbus-1-dev libglib2.0-dev pkg-config python3-dev
```

### For llama-cpp-python (LLM Backend)

If you encounter OpenMP linking errors during installation, use:

```bash
CMAKE_ARGS="-DGGML_BLAS=OFF -DGGML_OPENMP=OFF" pip install llama-cpp-python --no-cache-dir
```


## Installation Complete Checklist

- [x] Docker Compose v2 installed
- [x] System dependencies installed (libdbus, libglib)
- [x] Python packages installed
- [x] neuralux-common package installed
- [x] aish CLI tool installed
- [x] Infrastructure services running (docker compose ps)

## Next Steps

1. **Verify Services**: `docker compose ps` (should show all services Up)
2. **Test Infrastructure**: `python3 demo-without-model.py`
3. **Download Model** (optional, ~2GB): See QUICKSTART.md step 4
4. **Start LLM Service** (with model): `cd services/llm && python service.py`
5. **Use AI Shell**: `aish`

## Troubleshooting

### Conda Interference
If you see `(base)` in your prompt along with your venv, conda tools may interfere:
```bash
conda deactivate  # Exit conda base
```

### OpenMP Errors
If llama-cpp-python fails to build with OpenMP errors, disable OpenMP:
```bash
CMAKE_ARGS="-DGGML_BLAS=OFF -DGGML_OPENMP=OFF" pip install llama-cpp-python --no-cache-dir
```

### Package Import Errors
```bash
# Reinstall packages
pip install -e packages/common/ --force-reinstall
pip install -e packages/cli/ --force-reinstall
```

## Installation Completed
Date: October 25, 2025
Environment: myenv (Python 3.12.9)
Status: ✅ All packages installed successfully

