# Overlay Conversational Mode - Quick Start Guide

**Status**: ✅ Ready to Use  
**Version**: Phase 1-3 Complete

## 🚀 Getting Started

### 1. Enable Conversation Mode

When the overlay opens (Alt+Space), click the **💬 button** in the top toolbar to enable conversational mode.

**You'll see:**
- View switches to conversation history
- Input placeholder: "Type your message..."
- Status: "Conversational mode active"
- Empty state: "Start a conversation!"

### 2. Send Your First Message

Type a message and press **Enter**:

```
create a file named ideas.txt
```

**What happens:**
1. Your message appears (blue, right side)
2. "Thinking..." spinner shows
3. AI responds (gray, left side)
4. If actions need approval → Dialog appears
5. You approve → Actions execute
6. Result cards show what happened

### 3. Continue the Conversation

The AI remembers context! Try:

```
write 5 startup ideas in it
```

The AI knows "it" = the file you just created!

## 💡 Example Conversations

### File Creation Workflow

```
You: create a file notes.txt

AI: ✓ File created: ~/notes.txt
    [Command output card shows success]

You: write about quantum computing in it

AI: I've planned some actions...
    [Approval dialog shows: generate text + write file]

[You click "Approve All"]

AI: ✓ Generated content
    ✓ Written to notes.txt
    [LLM card shows generated text]
    [Command card shows write success]
```

### Image Generation Workflow

```
You: generate an image of a serene lake

AI: ✓ Image generated
    [Image card shows preview with save/copy buttons]

You: save it to my Pictures folder

AI: [Approval dialog for save operation]

[You approve]

AI: ✓ Image saved to ~/Pictures/serene_lake_20251028.png
```

### Web Search

```
You: search the web for Python 3.12 features

AI: ✓ Found 5 results
    [Web card shows links with snippets]
    [Open/Copy buttons for each]

You: open link 1

[Browser opens with the first result]
```

## 🎨 UI Elements

### Message Bubbles
- **Blue (right)**: Your messages
- **Gray (left)**: AI responses
- **Timestamp**: In corner
- **Copy button**: For long messages

### Action Cards

**Command Output Card** (💻)
- Shows command executed
- Exit code (✓ success / ✗ failed)
- stdout/stderr output
- Copy button

**LLM Generation Card** (🤖)
- Shows generated text
- Word/token count
- Copy and save buttons

**Image Card** (🎨)
- Image preview
- Prompt used
- Save, copy buttons
- Generation metadata

**Document Query Card** (📚)
- List of found documents
- Relevance scores
- Open buttons

**Web Search Card** (🌐)
- Search results with links
- Snippets
- Open in browser / copy URL

### Approval Dialog

When actions need your permission:

```
┌─────────────────────────────────┐
│ 🤖 Approval Required            │
├─────────────────────────────────┤
│                                 │
│ The AI wants to perform:        │
│                                 │
│ ☑ 1. Generate text              │
│    ✅ No approval needed         │
│                                 │
│ ☑ 2. Write to file              │
│    🔒 Requires approval          │
│    path: ~/notes.txt            │
│                                 │
│ ⚠️  1 action will modify files   │
│                                 │
│ [✓ Approve All]  [✗ Cancel]    │
└─────────────────────────────────┘
```

**Symbols:**
- ✅ = Automatic (safe, no approval needed)
- 🔒 = Needs approval (modifies system)

## ⌨️ Controls

### Buttons
- **💬** = Toggle conversation mode on/off
- **📋** = Switch back to traditional mode
- **🆕** = New conversation (clears history)
- **🕘** = Show conversation history

### In Conversation Mode
- **Enter** = Send message
- **Escape** = Close overlay
- **Click Copy** = Copy message/result
- **Click buttons** = Interact with results

## 🧠 What the AI Remembers

The AI maintains context including:

### Variables
- `last_created_file` → Most recent file you created
- `last_generated_image` → Most recent image generated
- `last_ocr_text` → Text from last OCR
- `last_generated_text` → Last LLM output
- `created_files` → List of all files created

### References
The AI understands:
- **"it"** → Last relevant object (file/image/text)
- **"that file"** → Last created file
- **"the image"** → Last generated image
- **"last one"** → Previous result

## 📁 Path Shortcuts

The AI expands common paths:

```
Pictures   → ~/Pictures
Desktop    → ~/Desktop
Documents  → ~/Documents
Downloads  → ~/Downloads
home       → ~
```

**Examples:**
```
> save it to Pictures
> create a file in Documents
> move it to Desktop
```

## 🔄 Switching Modes

### To Conversation Mode
1. Click 💬 button
2. History loads (if exists)
3. Continue previous conversation

### To Traditional Mode
1. Click 📋 button (shows while in conversation mode)
2. Returns to fuzzy search interface
3. Context still saved in background

You can switch back and forth anytime!

## ✅ Action Types

### Automatic (No Approval)
- LLM text generation
- Image generation (temp files)
- OCR operations
- Web search
- Document search
- File reading

### Needs Approval (🔒)
- File creation
- File writing
- File moving/deletion
- Image saving (to specific location)
- Command execution

## 🎯 Pro Tips

### 1. Chain Actions Naturally

Instead of:
```
> create file.txt
> write content in file.txt
```

Just say:
```
> create file.txt and write a summary of AI in it
```

### 2. Use References

Instead of:
```
> generate an image of sunset
> save /tmp/neuralux_img_123.png to Pictures
```

Just say:
```
> generate an image of sunset
> save it to Pictures
```

### 3. Be Specific When Needed

```
✓ Good: "create a file todo.txt"
✓ Good: "write 5 project ideas about AI"
✓ Good: "save it to Pictures as mountains.png"

✗ Too vague: "make a file"
✗ Too vague: "write something"
```

### 4. One Request Per Message

The AI handles multi-step, but keep it conversational:

```
✓ "create notes.txt and write about Python"
✗ "create notes.txt write about Python also search web and generate image"
```

### 5. Review Approvals

Always check the approval dialog:
- What commands will run?
- What files will be modified?
- Are the parameters correct?

## 🐛 Troubleshooting

### "Conversation handler not available"
**Solution**: Make sure services are running:
```bash
make start-all
```

### Actions hang or timeout
**Solution**: Check service logs:
```bash
tail -f data/logs/llm-service.log
tail -f data/logs/filesystem-service.log
```

### Context not persisting
**Solution**: Verify Redis is running:
```bash
docker ps | grep redis
```

### Dialog doesn't appear
**Solution**: Check for modal window issues, try clicking outside and inside the overlay.

## 📚 More Information

- **Full Documentation**: [CONVERSATIONAL_INTELLIGENCE.md](Documentation/CONVERSATIONAL_INTELLIGENCE.md)
- **Implementation Details**: [OVERLAY_CONVERSATIONAL_INTEGRATION.md](Documentation/OVERLAY_CONVERSATIONAL_INTEGRATION.md)
- **Enhancement Plan**: [OVERLAY_CONVERSATIONAL_ENHANCEMENT_PLAN.md](Documentation/OVERLAY_CONVERSATIONAL_ENHANCEMENT_PLAN.md)
- **Visual Mockups**: [OVERLAY_ENHANCEMENT_MOCKUP.md](Documentation/OVERLAY_ENHANCEMENT_MOCKUP.md)

## 🎉 Try It Now!

1. Open overlay: **Alt+Space**
2. Click **💬** button
3. Type: `create a file test.txt`
4. Press **Enter**
5. Watch the magic happen!

Then try:
```
> write a haiku about AI in it
> read it back to me
> generate an image of a robot writing poetry
> save it to Desktop
```

Welcome to the future of Neuralux! 🚀✨

