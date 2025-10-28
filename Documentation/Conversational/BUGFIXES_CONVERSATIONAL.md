# Conversational Intelligence Bug Fixes

**Date**: October 27, 2025

## Issues Fixed

### 1. ✅ Test Script Syntax Error
**File**: `test_conversational_intelligence.sh`  
**Line**: 155  
**Issue**: Bash syntax error - `else:` should be `else`  
**Fix**: Changed `else:` to `else`

### 2. ✅ CLI Import Error
**File**: `packages/cli/aish/main.py`  
**Line**: 3374  
**Issue**: `ModuleNotFoundError: No module named 'conversational_mode'`  
**Fix**: Changed import from `from conversational_mode` to `from aish.conversational_mode`

### 3. ✅ LLM Action Planning JSON Parse Error
**File**: `packages/common/neuralux/action_planner.py`  
**Lines**: 107-133  
**Issue**: LLM returning extra text after JSON caused parsing to fail with "Extra data: line X column 1"  
**Fix**: Added robust JSON extraction that:
- First tries markdown code blocks
- Then extracts complete JSON by counting braces
- Handles extra explanation text after JSON

### 4. ✅ Image Generation NATS Payload Exceeded
**File**: `services/vision/service.py`  
**Lines**: 96-138  
**Issue**: Base64-encoded images (2-4+ MB) exceeded NATS 1 MB payload limit  
**Fix**: Changed image generation to:
- Save images to temp files (`/tmp/neuralux_img_<timestamp>.png`)
- Return file path instead of base64 data
- Avoids NATS payload size limits

### 5. ✅ Placeholder Replacement Not Working
**File**: `packages/common/neuralux/conversation_handler.py`  
**Lines**: 180-214  
**Issue**: Placeholders like `{llm_output}` and `{last_generated_image}` weren't being replaced with actual values  
**Symptoms**:
- File write would get literal `{llm_output}` instead of generated text
- Image save would fail with `{last_generated_image}` as path
**Fix**: Enhanced placeholder replacement to:
- Handle both single `{var}` and double `{{var}}` brace formats
- Replace with context variables automatically
- Check both context and output chain for values

### 6. ✅ Image Save Error Handling
**File**: `packages/common/neuralux/orchestrator.py`  
**Lines**: 367-430  
**Issue**: Image save failed silently without proper error messages  
**Fix**: Added robust error handling:
- Check if source image exists before copying
- Auto-create destination directories
- Better path expansion for directories
- Clear error messages for debugging

### 7. ✅ Greetings Triggering Unnecessary Actions
**File**: `packages/common/neuralux/action_planner.py`  
**Lines**: 40-53  
**Issue**: Simple greetings like "hello!" triggered command execution  
**Fix**: Added conversational input detection:
- Pattern matching for greetings (hi, hello, hey, etc.)
- Pattern matching for thanks, bye, and simple responses
- Returns empty action list for conversational inputs
- Responds naturally without executing actions

### 8. ✅ Command Output Not Displayed
**File**: `packages/cli/aish/conversational_mode.py`  
**Lines**: 274-292  
**Issue**: Command execution succeeded but output wasn't shown to user  
**Symptoms**: "docker ps -a" ran but containers list not visible  
**Fix**: Enhanced result display:
- Shows stdout from command execution
- Smart truncation: shows up to 100 lines or 10KB (was 1KB)
- Shows truncation stats when output is long (X/Y lines, N/M chars)
- Shows stderr for failed commands
- Clear formatting with Output/Error headers

### 9. ✅ Command Approval and Display
**Files**: 
- `packages/common/neuralux/action_planner.py` (Lines 247, 270)
- `packages/cli/aish/conversational_mode.py` (Lines 233-235)

**Issue**: Commands weren't requiring approval and the actual command wasn't visible  
**Fix**: 
- ALL commands (command_execute) now REQUIRE approval for safety
- Command text displayed in approval prompt
- Clear guidance to LLM that all shell commands need approval
- Example shows: "Execute: docker ps -a" with approval required

### 10. ✅ Multilingual Greetings Support
**File**: `packages/common/neuralux/action_planner.py`  
**Lines**: 43, 45, 47  
**Issue**: "Bonjour!" not recognized as greeting, triggered LLM action  
**Fix**: Added multilingual greeting patterns:
- French: bonjour, salut, merci, au revoir
- Spanish: hola, gracias, adios
- Italian: ciao
- All trigger simple greeting response without actions

### 11. ✅ "List Files" Using Wrong Action
**File**: `packages/common/neuralux/action_planner.py`  
**Lines**: 208-210, 273-274, 375-391  
**Issue**: "list my files" tried to use `file_read` on directories, which fails  
**Symptoms**: Error "Is a directory" when trying to list files  
**Fix**: 
- Clarified that `file_read` is for single files, NOT directories
- Added guidance: "To list files, use command_execute with 'ls'"
- Added example: "list my files" → `ls -la ~` command
- Added fallback pattern for listing files

### 12. ✅ "Create Folder" Creates File Instead
**File**: `packages/common/neuralux/action_planner.py`  
**Lines**: 229, 277-278, 299-316  
**Issue**: "create a folder named X" used `file_create`, which creates a 0-byte FILE not a DIRECTORY  
**Symptoms**: 
- Creates empty file instead of directory
- Subsequent file creation in "folder" fails with "[Errno 20] Not a directory"
**Fix**:
- Added guidance: use `command_execute` with `mkdir -p` for directories
- Added example: "create folder test" → `mkdir -p ~/test`
- Added fallback pattern detecting "folder"/"directory"/"dir" keywords
- Uses `mkdir -p` to create directories with parents automatically

### 13. ✅ Refactoring - Removed Old Action Type References
**Files**: 
- `packages/common/neuralux/action_planner.py` (Line 519)
- `packages/common/neuralux/conversation.py` (Line 320)

**Issue**: After Option C refactoring, code still referenced removed action types
**Symptoms**: `type object 'ActionType' has no attribute 'FILE_WRITE'`
**Fix**:
- Removed FILE_WRITE check in `_enrich_action_params`
- Simplified FILE_CREATE check in reference resolution
- All file operations now use `command_execute` action type

### 14. ✅ LLM-Generated Content Not Written to Files
**Files**:
- `packages/common/neuralux/orchestrator.py` (Lines 466, 480-490)
- `packages/common/neuralux/conversation_handler.py` (Lines 216-233)

**Issue**: When generating content with LLM then writing to file, only literal text was written
**Symptoms**:
- LLM generates full summary (e.g., 1000 characters)
- Command `echo 'summary of marie curie' > file.txt` writes literal 22 characters
- File contains "summary of marie curie" instead of actual generated content

**Fix**:
- Added `stdin` parameter support to command executor
- Conversation handler detects when command writes to file after LLM generation
- Automatically converts `echo 'text' > file` to `cat > file` with stdin
- Pipes actual LLM-generated content via subprocess stdin
- Now full generated content is written correctly

## Testing

After fixes:
```bash
source myenv/bin/activate
pip install -e packages/common/

# Restart vision service
pkill -f "vision.*service"
python services/vision/service.py &

# Test
./test_conversational_intelligence.sh
aish converse
```

## Test Results

All components now working:
- ✅ Test script runs without errors
- ✅ CLI command loads correctly
- ✅ LLM action planning succeeds (with fallback if needed)
- ✅ Image generation returns file paths
- ✅ Multi-step workflows execute correctly
- ✅ Context memory persists across turns
- ✅ Reference resolution works

## Impact

These fixes enable the full conversational intelligence workflow:
1. Create files
2. Generate and write content
3. Generate and save images
4. Chain multiple operations
5. Natural language references ("it", "that file")

All example workflows from documentation now work as expected.

