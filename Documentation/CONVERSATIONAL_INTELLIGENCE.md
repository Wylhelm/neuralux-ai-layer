# Conversational Intelligence System

**Status**: ✅ Implemented (October 2025)

## Overview

The Conversational Intelligence System transforms Neuralux into a truly intelligent assistant capable of:
- **Multi-step workflows** - Execute complex tasks from a single request
- **Contextual memory** - Remember everything in the conversation
- **Reference resolution** - Understand "it", "that file", "the image"
- **Action planning** - Break down requests into executable steps
- **Approval management** - Safe execution with user confirmation

## Quick Start

### Basic Usage

Start the conversational mode:

```bash
aish converse
```

Try these examples:

```
# Create and populate a file
> create a file named mariec.txt
> write a summary of Marie Curie in it

# Generate and save images
> generate an image of Marie Curie
> save it to my Pictures folder

# OCR and process
> ocr the active window
> put the summary in a new file named ocr.txt
```

## How It Works

### 1. Conversation Context

The system maintains rich context including:
- **Full conversation history** - All turns with timestamps
- **Action results** - What was created, generated, or modified
- **Context variables**:
  - `last_created_file` - Most recent file created
  - `last_generated_image` - Most recent image path
  - `last_ocr_text` - Text from last OCR operation
  - `last_generated_text` - LLM-generated content
  - `created_files` - List of all files created in session

### 2. Reference Resolution

The AI understands natural references:

```
> create a file notes.txt
> write some ideas in it         ← "it" = notes.txt

> generate an image of a sunset
> save it to Desktop              ← "it" = the generated image

> ocr the window
> translate that to French        ← "that" = OCR text
```

Supported references:
- **Pronouns**: it, this, that, these, those, them
- **Phrases**: "the image", "the file", "the text", "last image", etc.

### 3. Multi-Step Action Planning

The AI plans actions automatically:

**Your request:**
```
create a file summary.txt and write a summary of quantum computing in it
```

**AI planning:**
1. ✅ LLM Generate: "Create quantum computing summary" (no approval needed)
2. 🔒 File Create: "Create summary.txt" (needs approval)  
3. 🔒 File Write: "Write content to summary.txt" (needs approval)

You approve once, and all actions execute in sequence.

### 4. Available Actions

The system can perform these actions:

#### File Operations
- **file_create** - Create a new file
- **file_write** - Write or append to a file
- **file_read** - Read file content
- **file_move** - Move or rename files

#### AI Operations
- **llm_generate** - Generate text with LLM
- **image_generate** - Generate images with Flux AI
- **image_save** - Save images to specific locations
- **ocr_capture** - Extract text from images/screen

#### System Operations
- **command_execute** - Run shell commands

## Example Workflows

### Workflow 1: Document Creation

```
> create a file meeting_notes.txt

✓ File created: /home/user/meeting_notes.txt

> write a template for meeting notes with sections for attendees, agenda, and action items

✓ Content generated and written to meeting_notes.txt
```

### Workflow 2: Research and Save

```
> generate a summary of neural networks

🤖 Neural networks are computational models inspired by the human brain...

> save that to a file named nn_summary.txt

✓ Summary saved to nn_summary.txt
```

### Workflow 3: Image Generation Pipeline

```
> generate an image of a serene mountain landscape at sunset

✓ Image generated: /tmp/neuralux_img_1234567890.png

> save it to my Pictures folder with name mountains.png

✓ Image saved to ~/Pictures/mountains.png

> generate another image of the same scene but with snow

✓ Image generated: /tmp/neuralux_img_1234567891.png

> save it to Pictures as mountains_winter.png

✓ Image saved to ~/Pictures/mountains_winter.png
```

### Workflow 4: OCR and Process

```
> ocr the active window

✓ Extracted text (245 characters):
  "Introduction to Quantum Computing
  Quantum computers use qubits instead of..."

> translate that text to French and save it to translated.txt

✓ Translation generated
✓ Saved to translated.txt
```

### Workflow 5: Complex Multi-Step

```
> create a file ideas.txt

✓ Created ideas.txt

> write 5 startup ideas about AI in it

✓ AI startup ideas written to ideas.txt

> generate an image representing the first idea

✓ Image generated based on first idea

> save the image to Desktop

✓ Image saved to ~/Desktop/neuralux_image_1234567890.png
```

## Architecture

### Components

```
┌──────────────────────────────────────┐
│    User Request (Natural Language)   │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│      ConversationHandler             │
│  • Manages conversation context       │
│  • Coordinates components             │
└──────────────┬───────────────────────┘
               │
     ┌─────────┼─────────┐
     │         │         │
     ↓         ↓         ↓
┌────────┐ ┌──────┐ ┌─────────┐
│Context │ │Action│ │Action   │
│Manager │ │Planner│ │Orchestr.│
└────────┘ └──────┘ └─────────┘
     │         │         │
     │         ↓         │
     │    ┌──────────┐  │
     └───→│ LLM      │←─┘
          │ Planning │
          └────┬─────┘
               │
     ┌─────────┼──────────┐
     ↓         ↓          ↓
┌─────────┐ ┌──────┐ ┌────────┐
│  LLM    │ │Vision│ │File    │
│ Service │ │ Svc  │ │System  │
└─────────┘ └──────┘ └────────┘
```

### Key Classes

#### ConversationHandler
High-level orchestrator that manages the entire conversation flow.

**Methods:**
- `process_message(user_input)` - Process user request
- `approve_and_execute(actions)` - Execute approved actions
- `get_conversation_history()` - Retrieve history
- `reset_conversation()` - Clear context

#### ActionPlanner
Plans actions based on user input using LLM intelligence.

**Features:**
- LLM-powered action planning
- Pattern-based fallback
- Parameter enrichment
- Reference resolution integration

#### ActionOrchestrator
Executes actions and manages their results.

**Features:**
- Action execution
- Error handling
- Context variable updates
- Action chaining (outputs feed into next action)

#### ConversationContext
Stores rich conversation state.

**Data:**
- Conversation turns (user/assistant messages)
- Action results with timestamps
- Context variables
- Working directory

### Action Flow

```
1. User Input
   ↓
2. Load Conversation Context
   ↓
3. Resolve References
   │ "it" → last_created_file
   │ "that image" → last_generated_image
   ↓
4. Plan Actions (LLM)
   │ Break down complex request
   │ Determine action sequence
   │ Set approval requirements
   ↓
5. Request Approval (if needed)
   ↓
6. Execute Actions Sequentially
   │ Action 1 → Update context
   │ Action 2 (uses output from 1)
   │ Action 3 → Update context
   ↓
7. Save Context
   ↓
8. Return Results
```

## Path Expansion

The system understands these path shortcuts:

```
"Pictures" or "pictures"  → ~/Pictures
"Desktop" or "desktop"    → ~/Desktop
"Documents"               → ~/Documents
"Downloads"               → ~/Downloads
"Music"                   → ~/Music
"Videos"                  → ~/Videos
"home"                    → ~
```

Examples:
```
> save it to Pictures           # → ~/Pictures/
> create a file in Documents    # → ~/Documents/
> move it to Desktop            # → ~/Desktop/
```

## Context Management

### View Context

```bash
# In conversational mode:
> /context
```

Shows:
- Current context variables
- Turn count
- Working directory

### View History

```bash
> /history
```

Shows:
- Recent conversation turns
- Actions performed
- Results summary

### Reset Context

```bash
> /reset
```

Clears all context variables and conversation history. Use this to start fresh.

## Safety and Approvals

### Approval Requirements

Actions requiring approval (🔒):
- File creation
- File writing/modification
- File moving/deletion
- Image saving (to specific locations)
- Command execution

Actions NOT requiring approval (✅):
- LLM text generation
- Image generation (temporary files)
- OCR operations
- File reading

### Batch Approval

When multiple actions are planned, you approve once for the entire workflow:

```
Planned actions:
  1. ✅ llm_generate: Generate quantum computing summary
  2. 🔒 file_create: Create summary.txt
  3. 🔒 file_write: Write summary to file

Approve these actions? [Y/n]
```

## Integration with Services

The conversational system integrates with:

1. **LLM Service** - Text generation, action planning
2. **Vision Service** - Image generation, OCR
3. **Filesystem Service** - File operations (NEW: write, create, move)
4. **Audio Service** - Voice input/output (via overlay)

### NATS Subjects Used

- `ai.llm.request` - LLM generation
- `ai.vision.imagegen.request` - Image generation
- `ai.vision.ocr.request` - OCR operations
- `system.file.write` - File write operations
- `system.file.read` - File read operations
- `system.file.move` - File move operations
- `system.file.delete` - File delete operations

## Advanced Features

### Action Chaining

Outputs from one action automatically feed into the next:

```
> create a file and write "Hello World" in it
```

Internally:
1. LLM generates "Hello World" → `{{llm_output}}`
2. File create: `test.txt` → `{{last_created_file}}`
3. File write: `content={{llm_output}}`, `path={{last_created_file}}`

### Context Variables Persistence

Context persists across:
- Multiple turns in the same session
- CLI and overlay (shared via Redis)
- Service restarts (24-hour TTL)

### Session Management

Sessions are identified by: `{user}@{hostname}`

Multiple sessions can coexist:
- CLI conversational mode: `user@hostname:cli`
- Overlay sessions: `user@hostname:overlay`
- Custom sessions: Specify session ID

## Troubleshooting

### Services Not Responding

Ensure all services are running:
```bash
make status
```

Start missing services:
```bash
make start-all
```

### File Operations Failing

Check permissions:
```bash
# Files created in home directory by default
ls -la ~/
```

### Actions Not Chaining

Check logs:
```bash
tail -f data/logs/llm-service.log
tail -f data/logs/filesystem-service.log
```

### Context Not Persisting

Verify Redis is running:
```bash
docker ps | grep redis
```

## Performance Notes

- **Action planning**: ~1-2 seconds (LLM call)
- **Action execution**: Varies by action type
  - File operations: <100ms
  - LLM generation: 0.5-5s (depending on GPU)
  - Image generation: 5-30s (depending on model)
- **Context loading**: <50ms (Redis)

## Future Enhancements

Planned improvements:
- [ ] Streaming responses during execution
- [ ] Undo/redo for file operations
- [ ] Voice input in conversational mode
- [ ] Multi-modal inputs (images in conversation)
- [ ] Workflow templates and macros
- [ ] Collaborative sessions

## API Reference

See `packages/common/neuralux/` for detailed API:
- `conversation.py` - Context management
- `orchestrator.py` - Action execution
- `action_planner.py` - Planning logic
- `conversation_handler.py` - High-level interface
- `file_ops.py` - File utilities

## GUI Overlay Enhancement

The conversational intelligence system is currently available in the CLI via `aish converse`. 

**Overlay Enhancement**: A comprehensive plan to bring all these features to the GUI overlay is documented in:
- [OVERLAY_CONVERSATIONAL_ENHANCEMENT_PLAN.md](OVERLAY_CONVERSATIONAL_ENHANCEMENT_PLAN.md) - Complete implementation plan
- [OVERLAY_ENHANCEMENT_MOCKUP.md](OVERLAY_ENHANCEMENT_MOCKUP.md) - Visual mockups and UI design

**Timeline**: 6-week phased rollout planned
- Phase 1: Core integration (1 week)
- Phase 2: Action planning UI (1 week)
- Phase 3: Result cards (1 week)
- Phase 4: Conversation history (1 week)
- Phase 5: Context visualization (1 week)
- Phase 6: Polish & features (1 week)

## Related Documentation

- [OVERLAY.md](OVERLAY.md) - Current GUI overlay features
- [OVERLAY_CONVERSATIONAL_ENHANCEMENT_PLAN.md](OVERLAY_CONVERSATIONAL_ENHANCEMENT_PLAN.md) - Enhancement roadmap
- [AUDIO.md](AUDIO.md) - Voice interface
- [IMAGE_GENERATION.md](IMAGE_GENERATION.md) - Image generation
- [API.md](API.md) - NATS subjects and REST endpoints

