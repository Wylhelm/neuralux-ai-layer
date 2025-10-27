# Bugfix: Command Execution Hang

## Issue
User reported: "it found the command but hang when I approved"

The command was correctly detected (e.g., "show me a tree of my home directory") and the user was prompted for approval, but the execution appeared to hang after approval.

## Root Cause

The original `_execute_command` function used `subprocess.run()` with `capture_output=True`, which buffers ALL output in memory before displaying it. For commands like `tree` that produce large amounts of output, this could:

1. **Appear to hang** - No output is shown until the entire command completes
2. **Consume excessive memory** - All output is buffered in memory
3. **Poor user experience** - User has no feedback during execution

### Original Code
```python
result = subprocess.run(
    command,
    shell=True,
    cwd=self.context['cwd'],
    capture_output=True,  # ← Buffers all output
    text=True,
    timeout=30,
)

if result.stdout:
    console.print(result.stdout)  # ← Only prints after completion
```

## Solution

Replaced buffered execution with **real-time streaming** using `subprocess.Popen`:

### New Code
```python
# Use Popen for real-time output streaming
process = subprocess.Popen(
    command,
    shell=True,
    cwd=self.context['cwd'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,  # Line buffered
)

# Stream output in real-time
if process.stdout:
    for line in process.stdout:
        console.print(line, end='')  # ← Prints immediately as generated
```

## Improvements

### 1. Real-Time Output Streaming
- Output appears immediately as the command generates it
- User sees progress in real-time
- No perception of "hanging"

### 2. Better Debugging
Added comprehensive logging:
```python
logger.debug("Starting command execution", command=command[:100])
logger.debug("Process started", pid=process.pid)
logger.debug("Command completed", returncode=returncode)
logger.error("Command execution error", error=str(e), command=command[:100])
```

### 3. Better Timeout Handling
```python
try:
    returncode = process.wait(timeout=30)
except subprocess.TimeoutExpired:
    logger.warning("Command timeout, killing process")
    process.kill()
    console.print("[red]Command timed out after 30 seconds[/red]")
```

### 4. Added User Approval Logging
```python
logger.debug("Waiting for user approval", command=command[:50])
if Confirm.ask("\nExecute this command?", default=False):
    logger.debug("User approved, executing command")
    await self._execute_command(command)
```

## Testing

Try these commands that generate lots of output:

```bash
aish
```

**Fast commands:**
```
> show me a tree of my home directory
→ Should stream output in real-time

> list all files in /etc
→ Should see files appearing immediately

> show me running processes
→ Should see process list streaming
```

**Slow commands:**
```
> find all files larger than 100MB
→ Should see results appearing as they're found

> search for python files in my home directory
→ Should see files streaming as they're discovered
```

## Expected Behavior

**Before:**
1. User: "show me a tree of my home directory"
2. System: [Shows command, asks for approval]
3. User: [Approves]
4. System: [Appears to hang... waiting... waiting...]
5. System: [Finally shows all output at once]

**After:**
1. User: "show me a tree of my home directory"
2. System: [Shows command, asks for approval]
3. User: [Approves]
4. System: "Executing..."
5. System: [Immediately starts showing tree output line by line]
6. System: "✓ Command completed successfully"

## Files Changed

- `packages/cli/aish/main.py`:
  - Modified `_execute_command()` to use `subprocess.Popen` with real-time streaming
  - Added debug logging for execution flow
  - Added approval logging
  - Better error handling and timeout management

## Status

✅ **Complete** - Changes applied and CLI package reinstalled.

## Additional Notes

If the issue persists, check the logs for:
- `"Waiting for user approval"` - Shows approval prompt was reached
- `"User approved, executing command"` - Shows user confirmed
- `"Starting command execution"` - Shows execution started
- `"Process started"` - Shows subprocess launched
- `"Command completed"` - Shows successful completion

If you see the logs stopping at a particular point, that will help identify where the actual hang is occurring.

