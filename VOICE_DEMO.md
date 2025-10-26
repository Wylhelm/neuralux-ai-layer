# Voice Assistant Demo Guide

## Quick Start

Try these voice interactions with your Neuralux assistant!

### 1. Single Turn Conversation

```bash
aish assistant
```

**What to say:**
- "Hello, what's your name?"
- "What can you do?"
- "Tell me a joke"
- "What is Linux?"

### 2. Continuous Conversation

```bash
aish assistant -c
```

**Example dialogue:**
1. "Hello"
   → Assistant introduces itself
2. "What's the weather like?"
   → Assistant explains how to check weather
3. "Show me how"
   → Assistant provides command
4. "Thank you"
   → Assistant responds politely
5. "Goodbye"
   → Exits conversation

### 3. Multi-Language Support

```bash
aish assistant
```

**Try different languages:**
- French: "Bonjour! Comment ça va?"
- Spanish: "Hola, ¿cómo estás?"
- German: "Hallo, wie geht es dir?"

The assistant will auto-detect and respond in your language!

### 4. Command Approval Workflow

```bash
aish assistant -c
```

**Example:**
1. Say: "List all the files in my home directory"
2. Assistant responds: "I'll run the command: ls -la ~. Should I proceed?"
3. When prompted, say: "Yes" or "No"
4. If you say "Yes":
   - Command executes
   - Full output shown on screen
   - Assistant speaks a summary of the results
5. If you say "No":
   - Command is cancelled

**More Examples:**
- "Show me the Python files" → `find . -name "*.py"`
- "Check my disk space" → `df -h`
- "What processes are running?" → `ps aux`
- "Find files named config" → `find . -name "*config*"`

### 5. Longer Recording

For complex questions or commands:

```bash
aish assistant -d 10
```

This gives you 10 seconds to speak instead of the default 5.

## Tips for Best Results

1. **Clear Audio**: Speak clearly and avoid background noise
2. **Microphone Distance**: 1-2 feet from microphone is ideal
3. **Pause Before Speaking**: Wait for the "Recording..." message
4. **Natural Speech**: Speak naturally, no need to shout
5. **Complete Sentences**: Full sentences work better than fragments

## Example Sessions

### Session 1: Information Request
```
You: "What is Neuralux?"
Assistant: "Neuralux is an AI assistant for Linux that helps with commands, 
           file management, and system tasks. How can I help you today?"
```

### Session 2: Task Request
```
You: "Can you check my disk space?"
Assistant: "I'll run the command: df -h. Should I proceed?"
You: "Yes please"
Assistant: "Okay, executing now"
[Command executes: df -h]
[Output displayed on screen]
Assistant: "Here are the first results: Filesystem Size Used Avail Use% Mounted on..."
```

### Session 3: File Search
```
You: "Hello"
Assistant: "Hello! How can I assist you today?"
You: "Find files named config"
Assistant: "I'll run the command: find . -name '*config*' -type f. Should I proceed?"
You: "Yes"
Assistant: "Okay, executing now"
[Command executes: find . -name '*config*' -type f]
[Output displayed on screen showing all config files]
Assistant: "Here are the first results: ./packages/common/neuralux/config.py. 
            There are more results shown on screen."
You: "Thank you"
Assistant: "You're welcome! Anything else I can help with?"
You: "Goodbye"
Assistant: "Goodbye! Have a great day!"
```

## Troubleshooting

### No Audio Heard
```bash
# Check if audio service is running
aish status | grep -i audio

# Test TTS directly
aish speak "Testing audio"
```

### Transcription Issues
```bash
# Test STT directly
aish listen --duration 5

# Try with more recording time
aish assistant -d 10
```

### LLM Not Responding
```bash
# Check LLM service
aish status | grep -i llm

# Restart services
make stop-all
make start-all
```

## Have Fun!

The voice assistant learns from context, so you can have natural multi-turn conversations. Try asking follow-up questions, giving complex commands, or just chatting!

Remember: Say "goodbye", "quit", or "exit" to end the conversation.
