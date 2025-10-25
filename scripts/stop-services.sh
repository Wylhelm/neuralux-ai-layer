#!/bin/bash
# Stop all Neuralux services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🛑 Stopping Neuralux AI Layer..."
echo ""

# Stop infrastructure services
echo "📦 Stopping infrastructure services..."
docker compose down

# Check for running LLM service
LLM_PID=$(pgrep -f "python.*service.py" || true)
if [ -n "$LLM_PID" ]; then
    echo "Stopping LLM service (PID: $LLM_PID)..."
    kill $LLM_PID
    echo "✓ LLM service stopped"
fi

echo ""
echo "✅ All services stopped!"

