#!/bin/bash
# Stop all Neuralux Python services and infrastructure

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RUN_DIR="$PROJECT_ROOT/data/run"

cd "$PROJECT_ROOT"

stop_service() {
  local name="$1"
  local pidfile="$RUN_DIR/${name}.pid"
  if [ -f "$pidfile" ]; then
    local pid
    pid=$(cat "$pidfile" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "⛔ Stopping $name (PID $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$pidfile"
  fi
}

for svc in llm filesystem health vision; do
  stop_service "$svc"
done

echo "📦 Stopping infrastructure (docker compose down)..."
docker compose down || true

echo "✅ All services and infrastructure stopped."


