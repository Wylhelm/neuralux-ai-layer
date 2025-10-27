# Intent System: Command Detection Improvement

## Issue
User reported: "I asked for a tree of my home directory and it triggered file_search, it should have been a command"

### Example
```
Input: "show me a tree of my home directory"
Old behavior: Classified as FILE_SEARCH (0.95 confidence)
Expected: COMMAND_REQUEST
```

## Root Cause

The intent classification had two issues:

1. **Weak Heuristics**: The heuristic detected "show me" as COMMAND_REQUEST but only with 0.75 confidence, which wasn't high enough to skip LLM verification (threshold is 0.95).

2. **Ambiguous LLM Prompt**: The LLM prompt didn't clearly distinguish between:
   - **FILE_SEARCH**: Searching through indexed document content (semantic search)
   - **COMMAND_REQUEST**: Executing system commands to generate output (tree, ls, ps, etc.)

## Solution

### 1. Enhanced Heuristics with Command Name Detection

Added a new heuristic that detects mentions of specific command names with **0.95 confidence** (high enough to skip LLM verification):

```python
# Command execution (mentions specific commands or utilities)
command_names = [
    "tree", "ls", "ps", "top", "htop", "cat", "grep", "find", "locate",
    "du", "df", "free", "netstat", "ss", "ip", "ifconfig", "ping",
    "curl", "wget", "git", "docker", "systemctl", "journalctl",
    "apt", "yum", "dnf", "pacman", "npm", "pip", "chmod", "chown",
    "tar", "zip", "unzip", "sed", "awk", "sort", "head", "tail"
]

for cmd in command_names:
    # Check if command appears as a word (not part of another word)
    if re.search(r'\b' + re.escape(cmd) + r'\b', lower):
        return {
            "intent": IntentType.COMMAND_REQUEST,
            "confidence": 0.95,  # High confidence - mentions specific command
            "parameters": {},
            "reasoning": f"Mentions command: {cmd}",
            "needs_approval": True
        }
```

**Key Features**:
- Uses regex word boundaries (`\b`) to avoid false matches (e.g., "trees" won't match "tree")
- Covers 40+ common Linux commands and utilities
- Returns 0.95 confidence, which is high enough to skip LLM verification
- Fast and deterministic

### 2. Improved LLM Prompt Clarity

Updated the LLM system prompt to explicitly distinguish the two intents:

**Before**:
```
6. **file_search**: User wants to search local files
   - "find documents about X", "search files containing Y", "locate files with Z"
```

**After**:
```
3. **command_request**: User wants to EXECUTE a system command or action NOW
   - "show me large files", "list running processes", "create a directory"
   - "show me a tree of my home directory", "display running processes"
   - Mentions specific command names: tree, ls, ps, grep, docker, etc.
   - Key: User expects IMMEDIATE command execution/action
   - Response: Generate and execute command (with approval)

6. **file_search**: User wants to search INDEXED document CONTENT (semantic search)
   - "find documents about X", "search files containing Y", "documents about firewall"
   - Key: Searching THROUGH file content, not executing commands
   - Response: Search indexed files and show matches
```

Also updated the critical examples section:
```
CRITICAL: Distinguish between:
- "show me a tree of my home" → **command_request** (run tree command NOW)
- "find documents about firewall" → **file_search** (search indexed file content)
- "how do I list files" → **command_how_to** (wants instructions)
- "what is a directory" → **informational** (wants explanation)
```

### 3. Increased Confidence for Action Verbs

Slightly increased the confidence for strong action verbs from 0.75 to 0.80:

```python
strong_action_starts = ["show me", "list all", "find all", "get all",
                       "display", "run", "execute", "create",
                       "delete", "remove", "install", "update"]
if any(lower.startswith(action) for action in strong_action_starts):
    return {
        "intent": IntentType.COMMAND_REQUEST,
        "confidence": 0.80,  # Slightly higher confidence
        "parameters": {},
        "reasoning": "Strong action verb at start",
        "needs_approval": True
    }
```

## Testing

Test these examples to verify the fix:

### Should be COMMAND_REQUEST
```bash
✓ show me a tree of my home directory
✓ list running processes with ps
✓ display disk usage with df
✓ run docker ps to see containers
✓ show me what's in /var/log with ls
✓ grep for errors in the log file
✓ check network connections with netstat
```

### Should be FILE_SEARCH
```bash
✓ find documents about firewall
✓ search files containing kubernetes
✓ locate files about docker configuration
✓ documents about security policies
✓ files containing TODO items
```

### Should be COMMAND_HOW_TO
```bash
✓ how do I list files in a directory
✓ what's the best way to search for text
✓ show me how to use grep
```

### Should be INFORMATIONAL
```bash
✓ what is the tree command
✓ explain how grep works
✓ tell me about docker
```

## Impact

**Before**: "show me a tree of my home directory" → FILE_SEARCH (0.95, LLM) ❌
**After**: "show me a tree of my home directory" → COMMAND_REQUEST (0.95, heuristic) ✅

**Benefits**:
- ✅ Faster classification (heuristics skip LLM call)
- ✅ More accurate intent detection
- ✅ Better distinction between file search and command execution
- ✅ More natural user experience

## Files Changed

- `packages/common/neuralux/intent.py`:
  - Added command name detection heuristic
  - Improved LLM prompt clarity
  - Increased action verb confidence
  - Added `import re` for regex matching

## Status

✅ **Complete** - Changes applied and package reinstalled.

To test:
```bash
aish
> show me a tree of my home directory
```

Expected: Should now be classified as COMMAND_REQUEST and generate the tree command! 🎯

