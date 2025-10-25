#!/bin/bash
# Start all Neuralux services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🚀 Starting Neuralux AI Layer..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Start infrastructure services
echo "📦 Starting infrastructure services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 5

# Check NATS
if curl -s http://localhost:8222/varz > /dev/null 2>&1; then
    echo "✓ NATS message bus is running"
else
    echo "⚠ Warning: NATS may not be running properly"
fi

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis cache is running"
else
    echo "⚠ Warning: Redis may not be running properly"
fi

# Check Qdrant
if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
    echo "✓ Qdrant vector store is running"
else
    echo "⚠ Warning: Qdrant may not be running properly"
fi

echo ""
echo "✅ Infrastructure services started!"
echo ""
echo "To start the LLM service, run:"
echo "  cd services/llm && python service.py"
echo ""
echo "Or run in background:"
echo "  cd services/llm && nohup python service.py > llm-service.log 2>&1 &"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"

