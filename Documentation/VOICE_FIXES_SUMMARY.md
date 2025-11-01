# Voice Detection Fixes Summary

## Issues Fixed

### 1. PyAudio Termination Bug (Critical)
**Problem:** Speech was not being detected because PyAudio was terminated before getting the audio sample width, causing silent exceptions.

**Fixed in:**
- `packages/overlay/overlay_window.py` - Conversational voice capture
- `packages/overlay/overlay_window.py` - Voice approval flow  
- `packages/cli/aish/main.py` - Traditional `/voice` command

**Change:** Get sample width BEFORE terminating PyAudio instance.

### 2. VAD Sensitivity Issues
**Problem:** Voice Activity Detection was stopping recording too early while you were still speaking.

**Fixed in:**
- `packages/overlay/overlay_window.py` - Removed hardcoded 0.8s cap on silence duration
- `packages/cli/aish/main.py` - Removed hardcoded 0.8s cap on silence duration

**Change:** Now respects the full `OVERLAY_VAD_SILENCE_DURATION` from .env

### 3. Language Detection Issues
**Problem:** System was using "auto" language detection, which incorrectly detected English as French.

**Fixed in:**
- `packages/overlay/config.py` - Added `stt_language` config parameter
- `packages/overlay/overlay_window.py` - Use configured language instead of "auto"
- `packages/cli/aish/main.py` - Use configured language instead of "auto"

**Change:** Now defaults to English ("en") and can be configured via `OVERLAY_STT_LANGUAGE` in .env

### 4. TTS Speaking Inappropriate Content
**Problem:** Text-to-speech was reading generic messages like "Answer user question completed successfully" instead of context-appropriate audio feedback.

**Fixed in:**
- `packages/overlay/overlay_window.py` - Added intelligent action-based TTS routing
- `packages/common/neuralux/conversation_handler.py` - Return actual LLM content, not completion messages
- `packages/common/neuralux/action_planner.py` - Removed rigid greeting patterns, let LLM handle naturally

**Change:** TTS now speaks appropriate content based on action type:
- Questions/conversation: Reads the actual AI-generated answer
- Commands: "Command executed successfully"
- Web searches: "Web search completed successfully"
- File searches: "File search completed successfully"
- Image generation: "Picture generated successfully"

### 5. Rigid Greeting Patterns
**Problem:** Using regex patterns to detect greetings was inflexible and missed variations like "hello how are you today".

**Fixed in:**
- `packages/common/neuralux/action_planner.py` - Removed all greeting patterns, let LLM be intelligent!

**Change:** All conversational inputs (greetings, questions, casual chat) now go directly to the LLM with a friendly system prompt. The LLM responds naturally to any greeting or conversational input.

## Configuration Guide

### Recommended .env Settings

```env
# Audio service
AUDIO_STT_DEVICE=auto
AUDIO_STT_COMPUTE_TYPE=float16
AUDIO_SERVICE_PORT=8006
AUDIO_STT_LANGUAGE=en
AUDIO_STT_MODEL=medium
AUDIO_TTS_MODEL=en_US-lessac-medium
AUDIO_TTS_SPEED=1.0
AUDIO_VAD_ENABLED=true

# Overlay conversational + VAD tuning
OVERLAY_TTS_ENABLED_DEFAULT=true
OVERLAY_STT_LANGUAGE=en                # Language for speech recognition
OVERLAY_VAD_SILENCE_THRESHOLD=180     # Fixed threshold (RMS) - use this instead of dynamic
OVERLAY_VAD_SILENCE_DURATION=1.5      # Seconds of silence before stopping (increase if cutting off)
OVERLAY_VAD_MIN_RECORDING_TIME=0.8    # Minimum recording time
OVERLAY_VAD_MAX_RECORDING_TIME=15     # Maximum recording time
OVERLAY_VAD_DYNAMIC_FACTOR=0.85       # Dynamic calibration factor (not used if threshold > 1)
OVERLAY_VAD_MIN_RMS=140               # Minimum RMS floor
```

### VAD Tuning Guide

#### If recording stops too early while speaking:
- **Increase** `OVERLAY_VAD_SILENCE_DURATION` (try 2.0 or 2.5)
- **Increase** `OVERLAY_VAD_SILENCE_THRESHOLD` (try 200 or 220)

#### If recording doesn't detect speech at all:
- **Decrease** `OVERLAY_VAD_SILENCE_THRESHOLD` (try 150 or 140)
- **Decrease** `OVERLAY_VAD_DYNAMIC_FACTOR` (try 0.7 or 0.6)

#### If recording continues too long after you stop speaking:
- **Decrease** `OVERLAY_VAD_SILENCE_DURATION` (try 1.0 or 0.8)

#### Dynamic vs Fixed Threshold:
- **Dynamic** (`OVERLAY_VAD_SILENCE_THRESHOLD=0.0`): Calibrates to background noise automatically
  - Good for: Varying environments
  - Bad for: High background noise

- **Fixed** (`OVERLAY_VAD_SILENCE_THRESHOLD=180`): Uses absolute RMS value
  - Good for: Consistent environment, high background noise
  - Bad for: Very quiet environments (set lower threshold)

### Language Settings

To change speech recognition language:
```env
OVERLAY_STT_LANGUAGE=en     # English (default)
OVERLAY_STT_LANGUAGE=fr     # French
OVERLAY_STT_LANGUAGE=es     # Spanish
OVERLAY_STT_LANGUAGE=de     # German
OVERLAY_STT_LANGUAGE=auto   # Auto-detect (not recommended - may be inaccurate)
```

## Testing After Changes

1. **Restart the overlay:**
   ```bash
   pkill -f "aish overlay"
   cd /home/guillaume/NeuroTuxLayer
   source myenv/bin/activate
   aish overlay --hotkey --tray &
   ```

2. **Test conversational mode:**
   - Press `Ctrl+Space`
   - Type `/start_chat` and press Enter
   - Click the microphone button
   - Speak clearly
   - Wait for automatic stop after silence

3. **Test traditional mode:**
   - Press `Ctrl+Space`
   - Type `/voice` or click microphone button
   - Speak clearly
   - Wait for automatic stop

## Troubleshooting

### "No speech detected"
- Check microphone is not muted
- Speak louder or closer to microphone
- Lower `OVERLAY_VAD_SILENCE_THRESHOLD`
- Run test: `python -c "import pyaudio; p = pyaudio.PyAudio(); print([p.get_device_info_by_index(i)['name'] for i in range(p.get_device_count())])"`

### Recording cuts off mid-sentence
- Increase `OVERLAY_VAD_SILENCE_DURATION` to 2.0 or higher
- Increase `OVERLAY_VAD_SILENCE_THRESHOLD` to require less aggressive silence detection

### Wrong language detected
- Set `OVERLAY_STT_LANGUAGE` explicitly (don't use "auto")
- Check `AUDIO_STT_LANGUAGE` matches in .env

### Recording continues too long
- Decrease `OVERLAY_VAD_SILENCE_DURATION` to 1.0 or 0.8
- Decrease `OVERLAY_VAD_MAX_RECORDING_TIME` if hitting max

## Files Modified

1. `packages/overlay/config.py` - Added `stt_language` parameter
2. `packages/overlay/overlay_window.py` - Fixed PyAudio bug, silence duration, language, TTS filtering
3. `packages/cli/aish/main.py` - Fixed PyAudio bug, silence duration, language
4. `packages/common/neuralux/conversation_handler.py` - Fixed LLM response message handling
5. `packages/common/neuralux/action_planner.py` - Improved greeting pattern recognition

All changes are backward compatible with existing configurations.

## TTS Behavior

The TTS system now intelligently speaks appropriate content based on action type:

**For Conversational Questions/Answers:**
- ✅ Speaks the actual AI-generated response
- Example: "How can you help me?" → Reads the full answer

**For Actions:**
- ✅ "Command executed successfully"
- ✅ "Web search completed successfully"
- ✅ "File search completed successfully"
- ✅ "Picture generated successfully"
- ✅ "Image saved successfully"
- ✅ "Text extracted successfully"

This provides clear audio feedback for background actions while preserving the full conversational experience for questions and answers.

