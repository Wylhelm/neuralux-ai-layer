#!/bin/bash
# Start infrastructure and all Neuralux Python services in the background

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data"
LOG_DIR="$DATA_DIR/logs"
RUN_DIR="$DATA_DIR/run"

mkdir -p "$LOG_DIR" "$RUN_DIR"

cd "$PROJECT_ROOT"

echo "🚀 Starting Neuralux (infra + services)..."

# Infra
if ! docker compose ps >/dev/null 2>&1; then
  echo "❌ Docker Compose not available. Please install Docker and Docker Compose."
  exit 1
fi

echo "📦 Starting infrastructure services (docker compose up -d)..."
docker compose up -d

echo "⏳ Waiting for services to initialize..."
sleep 3

# Choose Python interpreter
PY="$PROJECT_ROOT/myenv/bin/python"
if [ ! -x "$PY" ]; then
  PY="python3"
fi

start_service() {
  local name="$1"
  local dir="$PROJECT_ROOT/services/$name"
  local pidfile="$RUN_DIR/${name}.pid"
  local logfile="$LOG_DIR/${name}-service.log"

  if [ ! -d "$dir" ] || [ ! -f "$dir/service.py" ]; then
    return
  fi

  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile" 2>/dev/null)" 2>/dev/null; then
    echo "✓ $name service already running (PID $(cat "$pidfile"))"
    return
  fi

  echo "▶ Starting $name service..."
  (
    cd "$dir"
    # Set cuDNN library path for audio service (CUDA support)
    if [ "$name" = "audio" ]; then
      export LD_LIBRARY_PATH="$PROJECT_ROOT/myenv/lib/python3.12/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH"
    fi
    nohup "$PY" service.py > "$logfile" 2>&1 &
    echo $! > "$pidfile"
  )
  echo "✓ $name started (PID $(cat "$pidfile")) → logs: $logfile"
}

# Core services
for svc in llm filesystem health vision audio temporal agent system; do
  start_service "$svc"
done

echo ""
echo "✅ All available services started."
echo ""
echo "Useful commands:"
echo "  aish status                # Check service status"
echo "  tail -f $LOG_DIR/*         # View service logs"
echo "  ./scripts/stop-all.sh      # Stop everything"
echo ""
echo "Tip: Use 'make start-all' and 'make stop-all' as shortcuts."
