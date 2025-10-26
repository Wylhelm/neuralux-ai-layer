#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/data/logs"
RUN_DIR="$ROOT_DIR/data/run"
mkdir -p "$LOG_DIR" "$RUN_DIR"

echo "[smoke] Starting overlay (background with tray)"
nohup aish overlay --tray > "$LOG_DIR/overlay-smoke.log" 2>&1 &
PID=$!
echo $PID > "$RUN_DIR/overlay-smoke.pid"

sleep 2

echo "[smoke] Sending toggle"
aish overlay --toggle || true
sleep 1

echo "[smoke] Sending show"
aish overlay --show || true
sleep 1

echo "[smoke] Sending hide"
aish overlay --hide || true
sleep 1

echo "[smoke] Tail last 20 log lines"
tail -n 20 "$LOG_DIR/overlay-smoke.log" || true

echo "[smoke] Stopping overlay"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID" 2>/dev/null || true
  sleep 1
  kill -9 "$PID" 2>/dev/null || true
fi
rm -f "$RUN_DIR/overlay-smoke.pid"

echo "[smoke] Done"


