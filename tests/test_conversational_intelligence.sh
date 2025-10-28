#!/bin/bash
# Test script for conversational intelligence system

set -e

echo "🧠 Neuralux Conversational Intelligence Test Suite"
echo "=================================================="
echo

# Check if services are running
echo "1. Checking services..."
if ! docker ps | grep -q nats; then
    echo "❌ NATS not running. Starting services..."
    make start-infra
    sleep 2
fi

if ! pgrep -f "llm.*service" > /dev/null; then
    echo "⚠️  LLM service not running. Start with: python services/llm/service.py"
fi

if ! pgrep -f "filesystem.*service" > /dev/null; then
    echo "⚠️  Filesystem service not running. Start with: python services/filesystem/service.py"
fi

echo "✓ Infrastructure check complete"
echo

# Test 1: Import check
echo "2. Testing Python imports..."
python3 <<EOF
try:
    from neuralux import (
        ConversationContext,
        ConversationManager,
        ActionOrchestrator,
        ActionPlanner,
        ConversationHandler,
        FileOperations,
        PathExpander,
    )
    print("✓ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)
EOF

echo

# Test 2: Path expansion
echo "3. Testing path expansion..."
python3 <<'EOF'
from neuralux.file_ops import PathExpander
import os

tests = [
    ("~/test.txt", os.path.expanduser("~/test.txt")),
    ("Pictures/img.png", os.path.expanduser("~/Pictures/img.png")),
    ("Desktop", os.path.expanduser("~/Desktop")),
]

for input_path, expected in tests:
    result = PathExpander.expand(input_path)
    print(f"  {input_path} → {result}")
    if expected not in str(result):
        print(f"  ⚠️  Expected to contain: {expected}")

print("✓ Path expansion tests complete")
EOF

echo

# Test 3: Reference resolution
echo "4. Testing reference resolution..."
python3 <<'EOF'
from neuralux.conversation import ConversationContext, ReferenceResolver

# Create test context
ctx = ConversationContext(session_id="test", user_id="test")
ctx.set_variable("last_created_file", "/home/user/test.txt")
ctx.set_variable("last_generated_image", "/tmp/image.png")

tests = [
    ("write something in it", ["last_created_file"]),
    ("save it to Pictures", ["last_generated_image"]),
    ("copy that file", ["last_created_file"]),
]

print("Reference resolution tests:")
for text, expected_refs in tests:
    needs_res = ReferenceResolver.needs_resolution(text)
    if needs_res:
        resolved_text, resolved_values = ReferenceResolver.resolve(text, ctx)
        print(f"  ✓ '{text}'")
        print(f"    Resolved: {list(resolved_values.keys())}")
    else:
        print(f"  ⚠️  No resolution needed for: '{text}'")

print("✓ Reference resolution tests complete")
EOF

echo

# Test 4: File operations
echo "5. Testing file operations..."
python3 <<'EOF'
from neuralux.file_ops import FileOperations, PathExpander
from pathlib import Path
import tempfile
import os

# Create temp directory
with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test.txt"
    
    # Test create
    success, error = FileOperations.create_file(test_file, "Hello World")
    if success:
        print(f"  ✓ File created: {test_file}")
    else:
        print(f"  ❌ Create failed: {error}")
    
    # Test write
    success, error = FileOperations.write_file(test_file, "\nNew line", mode="a")
    if success:
        print(f"  ✓ File appended")
    else:
        print(f"  ❌ Write failed: {error}")
    
    # Test read
    success, content, error = FileOperations.read_file(test_file)
    if success:
        print(f"  ✓ File read: {len(content)} bytes")
        print(f"    Content: {repr(content)}")
    else:
        print(f"  ❌ Read failed: {error}")
    
    # Test move
    new_path = Path(tmpdir) / "moved.txt"
    success, error = FileOperations.move_file(test_file, new_path)
    if success:
        print(f"  ✓ File moved to: {new_path}")
    else:
        print(f"  ❌ Move failed: {error}")
    
    print("✓ File operations tests complete")
EOF

echo

# Test 5: CLI command availability
echo "6. Testing CLI commands..."
if aish --help | grep -q "converse"; then
    echo "  ✓ 'aish converse' command available"
else
    echo "  ❌ 'aish converse' command not found"
    echo "     Run: pip install -e packages/cli/"
fi

echo

echo "=================================================="
echo "✨ Test suite complete!"
echo
echo "Next steps:"
echo "1. Start all services: make start-all"
echo "2. Try conversational mode: aish converse"
echo "3. Test workflows:"
echo "   > create a file named test.txt"
echo "   > write 'Hello AI' in it"
echo
echo "See Documentation/CONVERSATIONAL_INTELLIGENCE.md for examples"

