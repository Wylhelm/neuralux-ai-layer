# 🧠 Conversational Intelligence - Quick Start

**NEW**: Experience natural, multi-step conversations with AI! ✨

## What Is It?

Neuralux now understands context and can handle complex, multi-step workflows naturally. You can:
- Create and populate files in one conversation
- Generate and save images seamlessly
- Chain multiple operations together
- Use natural references like "it", "that file", "the image"

## 5-Minute Quick Start

### 1. Start All Services

```bash
cd ~/NeuroTuxLayer
make start-all
```

Wait ~10 seconds for services to initialize.

### 2. Launch Conversational Mode

```bash
aish converse
```

### 3. Try Your First Workflow

**Example 1: Create and Populate a File**
```
You: create a file named todo.txt
AI: ✓ Created todo.txt

You: write a list of 5 project ideas in it
AI: Planned actions:
    1. ✅ llm_generate: Generate project ideas
    2. 🔒 file_write: Write to todo.txt
    Approve? [Y/n] y
AI: ✓ Completed 2 actions successfully

You: read the file
AI: [Shows content of todo.txt]
```

**Example 2: Generate and Save Image**
```
You: generate an image of a futuristic city
AI: ✓ Image generated: /tmp/neuralux_img_1234567890.png

You: save it to my Pictures folder
AI: ✓ Image saved to ~/Pictures/neuralux_image_1234567890.png
```

**Example 3: OCR Workflow**
```
You: ocr the active window
AI: ✓ Extracted text (342 characters)

You: summarize that in a file named summary.txt
AI: Planned actions:
    1. ✅ llm_generate: Summarize OCR text
    2. 🔒 file_create: Create summary.txt
    3. 🔒 file_write: Write summary
    Approve? [Y/n]
```

## Key Commands

While in conversational mode:

| Command | Description |
|---------|-------------|
| `/reset` | Clear conversation context and start fresh |
| `/history` | Show recent conversation turns |
| `/context` | View current context variables |
| `help` | Show help and examples |
| `exit` | Exit conversational mode |

## How It Works

### Contextual Memory
The AI remembers:
- What files you created
- What images you generated
- What text was extracted
- Everything in the conversation

### Reference Resolution
Use natural language:
- **"it"** - refers to the last relevant thing
- **"that file"** - the last file you worked with
- **"the image"** - the last image generated
- **"that text"** - the last text extracted

### Multi-Step Planning
Complex requests are automatically broken down:

```
You: create notes.txt and write about quantum computing in it

AI internally plans:
  1. Generate text about quantum computing (LLM)
  2. Create file notes.txt
  3. Write content to notes.txt
  
Then asks for ONE approval for all steps!
```

## Real-World Examples

### Academic Research
```
You: create research_notes.txt
You: write a summary of recent advances in quantum computing in it
You: generate an image representing quantum entanglement
You: save the image to my Documents folder
```

### Creative Writing
```
You: create story.txt
You: write the first paragraph of a sci-fi story about AI in it
You: generate an image of the story's setting
You: save it to Desktop as story_cover.png
```

### Documentation
```
You: ocr this documentation page
You: extract the key points and save them to key_points.txt
You: translate those key points to French
You: save the translation to key_points_fr.txt
```

## Path Shortcuts

Use these shortcuts for common folders:

| Shortcut | Expands To |
|----------|-----------|
| `Pictures` | `~/Pictures/` |
| `Desktop` | `~/Desktop/` |
| `Documents` | `~/Documents/` |
| `Downloads` | `~/Downloads/` |
| `Music` | `~/Music/` |
| `Videos` | `~/Videos/` |

Examples:
```
> save it to Pictures
> create a file in Documents
> move it to Desktop
```

## Action Types

### File Operations (Require Approval)
- Create, write, move, delete files
- Read files (no approval needed)

### AI Operations
- Generate text (no approval)
- Generate images (no approval)
- Save images (requires approval)
- OCR capture (no approval)

### Why Approvals?
Actions that modify your filesystem require approval for safety. Reading and generating content (temporary) don't need approval.

## Tips for Best Results

1. **Be Natural**: Talk normally, don't use special syntax
   - ✅ "create a file and write about AI in it"
   - ❌ "FILE_CREATE(name.txt); WRITE(content)"

2. **Use References**: Leverage contextual memory
   - ✅ "save it to Pictures"
   - ❌ "save /tmp/img_123.png to ~/Pictures/"

3. **Chain Operations**: Do complex tasks in one go
   - ✅ "create todo.txt and write 5 ideas in it"
   - ❌ Separate: "create todo.txt" then "write ideas"

4. **Check Context**: Use `/context` to see what the AI remembers

5. **Reset When Needed**: Use `/reset` to start fresh conversations

## Troubleshooting

### Services Not Responding
```bash
# Check service status
make status

# Restart if needed
make restart
```

### File Not Created
- Check approval was given
- Verify path permissions
- Check logs: `tail -f data/logs/filesystem-service.log`

### Context Not Working
```bash
# Verify Redis is running
docker ps | grep redis

# Restart Redis if needed
docker restart neuralux-redis
```

### CLI Command Not Found
```bash
# Reinstall CLI
pip install -e packages/cli/
pip install -e packages/common/
```

## Next Steps

1. **Read Full Documentation**
   - [CONVERSATIONAL_INTELLIGENCE.md](Documentation/CONVERSATIONAL_INTELLIGENCE.md)
   - Detailed examples and API reference

2. **Test Advanced Features**
   ```bash
   ./test_conversational_intelligence.sh
   ```

3. **Try Complex Workflows**
   - Multi-file operations
   - Image generation pipelines
   - OCR + processing workflows

4. **Explore Integrations**
   - Voice input (coming to conversational mode)
   - Overlay UI (enhancement in progress)

## Getting Help

- **Documentation**: See `Documentation/` folder
- **Examples**: In CONVERSATIONAL_INTELLIGENCE.md
- **Logs**: Check `data/logs/*.log` files
- **Test**: Run `test_conversational_intelligence.sh`

## What's Next?

This is just the beginning! Upcoming features:
- Full overlay UI with conversation history
- Streaming responses
- Voice input in conversational mode
- Workflow templates and macros
- Multi-modal inputs (images in conversation)

---

**Happy conversing!** 🚀

Try: `aish converse` to get started!

