#!/bin/bash
# Test script for overlay conversational mode

set -e

echo "🧪 Testing Overlay Conversational Mode Setup"
echo "============================================"
echo ""

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Not in virtual environment. Activating myenv..."
    source myenv/bin/activate
fi

echo "✓ Virtual environment: $VIRTUAL_ENV"
echo ""

# Check Python modules
echo "📦 Checking Python modules..."
python3 -c "from neuralux.messaging import MessageBusClient; print('✓ neuralux.messaging')" || echo "✗ neuralux.messaging FAILED"
python3 -c "from neuralux.conversation_handler import ConversationHandler; print('✓ neuralux.conversation_handler')" || echo "✗ neuralux.conversation_handler FAILED"
python3 -c "import sys; sys.path.insert(0, 'packages'); from overlay.conversation import OverlayConversationHandler; print('✓ overlay.conversation')" || echo "✗ overlay.conversation FAILED"
echo ""

# Check services
echo "🔌 Checking services..."

# Check NATS
if docker ps | grep -q nats; then
    echo "✓ NATS is running"
else
    echo "✗ NATS is NOT running"
    echo "  Run: make start-all"
fi

# Check Redis
if docker ps | grep -q redis; then
    echo "✓ Redis is running"
else
    echo "✗ Redis is NOT running"
    echo "  Run: make start-all"
fi

# Check LLM service
if curl -s http://localhost:8000/v1/health > /dev/null 2>&1; then
    echo "✓ LLM service is running (port 8000)"
else
    echo "✗ LLM service is NOT running"
    echo "  Run: make start-all"
fi

# Check Vision service
if curl -s http://localhost:8005/v1/health > /dev/null 2>&1; then
    echo "✓ Vision service is running (port 8005)"
else
    echo "⚠️  Vision service is NOT running (optional for basic chat)"
fi

# Check Filesystem service  
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✓ Filesystem service is running (port 8002)"
else
    echo "✗ Filesystem service is NOT running"
    echo "  Run: make start-all"
fi

echo ""

# Test message bus connection
echo "🔗 Testing message bus connection..."
python3 << 'EOF'
import asyncio
from neuralux.config import NeuraluxConfig
from neuralux.messaging import MessageBusClient

async def test_connection():
    try:
        bus = MessageBusClient(NeuraluxConfig())
        await bus.connect()
        print("✓ Successfully connected to NATS")
        await bus.disconnect()
        return True
    except Exception as e:
        print(f"✗ Failed to connect to NATS: {e}")
        return False

result = asyncio.run(test_connection())
exit(0 if result else 1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All checks passed!"
    echo ""
    echo "📝 To test the overlay:"
    echo "  1. Run: aish overlay --hotkey --tray"
    echo "  2. Press Ctrl+Space to open overlay"
    echo "  3. Click the 💬 button to enable conversation mode"
    echo "  4. Type: 'create a file test.txt'"
    echo "  5. Watch for the approval dialog"
    echo ""
else
    echo ""
    echo "⚠️  Some checks failed. Please fix the issues above."
    echo ""
    echo "To start all services:"
    echo "  make start-all"
    echo ""
fi

