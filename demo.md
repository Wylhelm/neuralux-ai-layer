## Neuralux Demo Script (CLI + GUI)

This step-by-step plan demonstrates Neuralux via the CLI (`aish`) and the GUI overlay. It’s designed to be copy-paste friendly with verification checkpoints and quick troubleshooting.

### What you’ll demo
- CLI assistant: natural language to commands, explanations, health, web, search
- Voice: STT, TTS, assistant
- GUI overlay: hotkey/tray, approvals, OCR, voice, web search
- Health dashboard and service status

---

## 0) Quick Smoke Test (no model)

Purpose: Validate core infrastructure connectivity without downloading a model.

```bash
python3 demo-without-model.py
```

Expected:
- Connects to NATS and returns a basic response. If this fails, fix infra first (see Troubleshooting).

---

## 1) Setup

### 1.1 Prerequisites
- Docker & Docker Compose, Python 3.10+, Git
- Optional (GUI overlay): GTK4 packages

Ubuntu/Debian (GUI deps):
```bash
sudo apt update
sudo apt install -y python3-gi gir1.2-gtk-4.0 libgtk-4-1 libgtk-4-bin
```

### 1.2 Start infrastructure
```bash
docker compose up -d
docker compose ps           # verify: all show "Up"
```

### 1.3 Install Python packages
```bash
pip install -r requirements.txt
pip install -e packages/common/
pip install -e packages/cli/
```

### 1.4 Download an LLM model (recommended 3B Q4_K_M)
```bash
mkdir -p models
wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  -O models/llama-3.2-3b-instruct-q4_k_m.gguf
```

### 1.5 Start the LLM service
Terminal A:
```bash
cd services/llm
python service.py
```

Expected:
- Logs show “Model loaded successfully” and Uvicorn running on http://0.0.0.0:8000

Optional verification (new terminal):
```bash
curl http://localhost:8000/
curl http://localhost:8222/varz   # NATS monitor
```

---

## 2) CLI Demo (aish)

Start the AI shell:
```bash
aish
```

### 2.1 Natural language → command (with approval)
At the prompt:
```
show me large files in my downloads folder
```
Expected:
- Shows a proposed shell command and asks for approval before running.

### 2.2 Explain a command
```
/explain docker compose ps
```
Expected:
- Markdown explanation of flags and behavior.

### 2.3 Service status
```
status
```
or from system shell:
```bash
aish status
```
Expected:
- ✓ Message bus: Connected; ✓ LLM service: Running

### 2.4 Health dashboard
```bash
aish health
aish health --watch
```
Expected:
- CPU/Mem/Disk/Net metrics; alerts if thresholds exceeded.

### 2.5 Web search with summaries
```
/web how to check gpu utilization on linux
```
Expected:
- Summaries with approval prompt before opening URLs.

### 2.6 Semantic indexing and search
From a system shell:
```bash
aish index ~/Documents
```
Then in `aish`:
```
find files about docker configuration
```
Expected:
- Semantic file results with relevance.

### 2.7 Voice: STT and TTS
From a system shell:
```bash
aish listen                # Record 5s and transcribe
aish listen --file audio.wav
aish speak "Hello from Neuralux!" --speed 1.2
```
Expected:
- Transcriptions printed; audio synthesized to speakers or file (if --output given).

### 2.8 Voice Assistant (single turn / continuous)
```bash
aish assistant             # Single turn
aish assistant -c          # Continuous mode
```

---

## 3) GUI Overlay Demo

### 3.1 Launch overlay (recommended)
```bash
aish overlay --hotkey --tray
```
Notes:
- The `--hotkey` flag is required for Ctrl+Space (X11 only).
- On Wayland, bind a desktop shortcut to run: `aish overlay --toggle`.

Control an existing instance (works on Wayland too):
```bash
aish overlay --toggle
aish overlay --show
aish overlay --hide
```

### 3.2 Basic interaction
1) Press Ctrl+Space (X11) or use tray → Toggle.
2) Type: “summarize recent system resource usage”.
3) Approve or Cancel any proposed action (command/file/URL).

Expected:
- Result area shows the LLM response; approvals required for actions.

### 3.3 Web search in overlay
- Type: `/web best way to monitor disk io on linux`
- Approve before opening a link.

### 3.4 OCR actions
1) Pick suggestion “OCR active window” or type: `/ocr window`
2) After OCR result appears, use buttons: Copy, Summarize, Translate, Extract table
3) Click “Continue chat” to ask follow-ups using the OCR text context
4) Click “Start fresh” to clear the session

Expected:
- OCR text rendered; action buttons operate on the captured text; session shared with CLI for 24h.

### 3.5 Voice in overlay
- Click Mic (🎤): capture → STT → LLM → show response
- Toggle Speaker (🔇/🔊): enable/disable auto TTS of results

### 3.6 Health in overlay
- Open the health view/suggestion to see CPU/Mem/Disk/Net and top processes; GPU if available.

### 3.7 Tray controls (optional)
- Ensure AppIndicator support is installed (see Troubleshooting).
- Use tray icon to toggle/show/hide overlay.

---

## 4) Verification Checkpoints
- `docker compose ps` shows services “Up”
- `curl http://localhost:8222/varz` returns NATS metrics
- LLM service logs show model loaded and Uvicorn running (http://localhost:8000)
- `aish status` shows ✓ for bus and LLM
- Overlay toggles and responds to queries; approvals are required before actions
- OCR, voice STT/TTS, and web search work from CLI and overlay

---

## 5) Troubleshooting

### Services won’t start / not reachable
```bash
docker compose down
docker compose up -d
docker compose logs -f
```

### NATS not connecting
```bash
curl http://localhost:8222/varz
docker compose restart nats
```

### aish not found
```bash
export PATH="$HOME/.local/bin:$PATH"
pip install -e packages/cli/
```

### Model/LLM issues
```bash
ls -lh models/
export LLM_GPU_LAYERS=0   # CPU mode fallback
```

### Overlay behind other windows (X11)
```bash
sudo apt install -y wmctrl
wmctrl -x -r com.neuralux.overlay -b add,above,sticky
```

### Tray not visible (Ubuntu/Debian)
```bash
sudo apt install -y gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1
```

### Wayland hotkey
- Bind a desktop shortcut to run: `aish overlay --toggle`

---

## 6) Clean Up
```bash
aish exit            # if in interactive shell
docker compose down
```

Optional full reset:
```bash
docker compose down -v
```

---

## 7) Appendix: Handy Commands
```bash
make start-all                 # (alt) start infra + services in background
make stop-all                  # stop everything
aish web "nvidia gpu usage linux" --limit 5
aish speak "Demo complete" --output demo.wav
```


