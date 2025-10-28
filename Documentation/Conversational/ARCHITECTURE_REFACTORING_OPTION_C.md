# Conversational Intelligence - Architecture Refactoring (Option C: Hybrid)

**Date**: October 27, 2025  
**Status**: ✅ Complete  
**Type**: Major refactoring to pure command-line assistant with AI superpowers

## Why This Change?

**Goal**: Create a true command-line assistant where users always see the exact commands that will run.

**Problem with old approach**: Mixed specialized file actions (`file_create`, `file_write`, etc.) with command execution created inconsistency and obscured what was actually happening.

## New Architecture: Option C (Hybrid)

### AI-Specific Actions (NOT shell commands)
These are capabilities that aren't available as shell commands:

1. **`llm_generate`** - AI text generation
2. **`image_generate`** - AI image generation (Flux/SDXL) 
3. **`image_save`** - Save AI-generated images
4. **`ocr_capture`** - Extract text from images/screen
5. **`document_query`** - Search indexed documents (RAG)

### Generic Command Execution
Everything else uses shell commands:

6. **`command_execute`** - ANY shell command (ALWAYS requires approval)

## What Changed

### Removed Action Types
- ❌ `file_create` → use `touch` or `echo >`
- ❌ `file_write` → use `echo >` or `cat >`  
- ❌ `file_read` → use `cat`
- ❌ `file_move` → use `mv`

### Added Action Types
- ✅ `document_query` - Search your indexed documents

### Modified Files
- `packages/common/neuralux/conversation.py` - Updated ActionType enum
- `packages/common/neuralux/orchestrator.py` - Removed file handlers, added document_query
- `packages/common/neuralux/action_planner.py` - Complete rewrite of planning prompts and fallback patterns

## Example Workflows

### Old Way (Before):
```
> create a file named test.txt
Planned actions:
  1. 🔒 file_create: Create test.txt
     path: test.txt

> write "hello" in it
Planned actions:
  1. 🔒 file_write: Write to test.txt
     path: test.txt
     content: hello
```

**Problem**: You don't see what's actually happening under the hood.

### New Way (After):
```
> create a file named test.txt
Planned actions:
  1. 🔒 command_execute: Create file
     command: touch test.txt

Approve? [y/n]

> write "hello world" in it
Planned actions:
  1. 🔒 command_execute: Write to file
     command: echo 'hello world' > test.txt

Approve? [y/n]
```

**Benefit**: You see the EXACT command that will run. Educational and transparent!

## Benefits

### 1. Transparency
- Users always see exact commands
- Educational - learn shell commands
- No "magic" happening behind the scenes

### 2. Simplicity
- Fewer action types to maintain
- Standard shell commands everyone knows
- Easier to extend (any command works)

### 3. Flexibility
- User can suggest any shell command
- Natural integration with existing workflows
- Works with pipes, redirects, etc.

### 4. Safety
- EVERY command requires approval
- User sees exactly what will execute
- Full control and visibility

## New Workflow Examples

### File Operations
```
> create notes.txt with "TODO: finish project" in it
Planned actions:
  1. 🔒 command_execute: Execute: echo 'TODO: finish project' > notes.txt
     command: echo 'TODO: finish project' > notes.txt

> read that file
Planned actions:
  1. 🔒 command_execute: Execute: cat notes.txt
     command: cat notes.txt

> create a folder named projects
Planned actions:
  1. 🔒 command_execute: Execute: mkdir -p ~/projects
     command: mkdir -p ~/projects
```

### AI + Commands
```
> generate a summary of quantum computing
Planned actions:
  1. ✅ llm_generate: Generate quantum computing summary
     prompt: Write a concise summary of quantum computing

> save that to quantum.txt
Planned actions:
  1. 🔒 command_execute: Execute: cat > quantum.txt (with generated content)
     command: cat > quantum.txt
```

### Document Search (NEW!)
```
> search my documents for Python tutorials
Planned actions:
  1. ✅ document_query: Search: Python tutorials
     query: Python tutorials
     limit: 10

Result: Found 15 documents about Python tutorials
  - tutorial_python_basics.md
  - python_advanced_concepts.pdf
  - ...
```

### Image Generation
```
> generate an image of a futuristic city
Planned actions:
  1. ✅ image_generate: Generate futuristic city image
     prompt: futuristic city with towering skyscrapers

> save it to Pictures
Planned actions:
  1. 🔒 image_save: Save to Pictures folder
     from: /tmp/neuralux_img_123.png
     to: ~/Pictures
```

### OCR + Processing
```
> ocr the active window
Planned actions:
  1. ✅ ocr_capture: Capture text from screen

> save the extracted text to ocr_output.txt
Planned actions:
  1. 🔒 command_execute: Execute: cat > ocr_output.txt
     command: cat > ocr_output.txt
```

## Action Approval Requirements

| Action Type | Requires Approval | Why |
|-------------|-------------------|-----|
| `llm_generate` | ❌ No | Generating text is safe |
| `image_generate` | ❌ No | Generating image is safe |
| `image_save` | ✅ Yes | Writes to filesystem |
| `ocr_capture` | ❌ No | Just reading screen |
| `document_query` | ❌ No | Just searching |
| `command_execute` | ✅ Yes (ALWAYS) | Can do anything! |

## Key Principle

**"If it modifies the system, you approve it and see the exact command."**

This makes Neuralux a true **command-line AI assistant** that:
- Enhances your CLI experience
- Shows you what it's doing
- Teaches you commands
- Gives you full control

## Migration Guide

If you had code using old actions:

### Before:
```python
Action(
    action_type=ActionType.FILE_CREATE,
    params={"file_path": "test.txt"},
    needs_approval=True
)
```

### After:
```python
Action(
    action_type=ActionType.COMMAND_EXECUTE,
    params={"command": "touch test.txt"},
    needs_approval=True
)
```

## Testing

Test the new architecture:
```bash
aish converse
```

Try these:
```
> create test.txt
> write "hello" in it
> read test.txt
> search my documents for AI
> generate an image of a robot
> save it to Desktop
```

You should see exact commands for approval!

## Future Enhancements

With this architecture, we can easily add:
- Command history and suggestions
- Command explanations ("what does this do?")
- Command templates/macros
- Integration with existing shell aliases
- Support for pipes and complex commands

---

**This is now a TRUE command-line AI assistant!** 🚀

