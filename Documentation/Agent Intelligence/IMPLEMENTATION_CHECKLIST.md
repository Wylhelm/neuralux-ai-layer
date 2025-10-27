# Intent System Implementation Checklist

## Pre-Integration Testing

- [ ] **Test the intent classifier standalone**
  ```bash
  source myenv/bin/activate
  python test_intent_system.py
  ```
  - Should show ~85%+ success rate
  
- [ ] **Try interactive mode**
  ```bash
  python test_intent_system.py --interactive
  ```
  - Test: "hello", "what is docker?", "show me large files"
  - Verify intents are classified correctly

- [ ] **Review the documentation**
  - [ ] Read `AGENT_INTELLIGENCE_SUMMARY.md`
  - [ ] Skim `AGENT_INTELLIGENCE_ANALYSIS.md`
  - [ ] Review `INTEGRATION_GUIDE.md`
  - [ ] Check `BEFORE_AFTER_FLOW.md` for examples

## Phase 1: CLI Integration (Quick Win)

### Step 1: Import Intent System

- [ ] Open `packages/cli/aish/main.py`
- [ ] Add imports at top:
  ```python
  from neuralux.intent import IntentClassifier, IntentType
  from neuralux.intent_handlers import IntentHandlers, IntentRouter
  ```

### Step 2: Initialize in AIShell

- [ ] In `AIShell.__init__()`, add:
  ```python
  self.intent_classifier = None
  self.intent_handlers = None
  self.intent_router = None
  ```

- [ ] In `AIShell.connect()`, after message bus connection:
  ```python
  if self.message_bus:
      self.intent_classifier = IntentClassifier(self.message_bus)
      self.intent_handlers = IntentHandlers(
          self.message_bus,
          context_getter=self._get_context_info
      )
      self.intent_router = IntentRouter(self.intent_handlers)
  ```

### Step 3: Add Process Method

- [ ] Add new method to `AIShell`:
  ```python
  async def process_with_intent(self, user_input: str, context: dict = None) -> dict:
      """Process user input using intent classification."""
      # Copy implementation from INTEGRATION_GUIDE.md
  ```

- [ ] Add helper methods:
  ```python
  async def _handle_web_search(self, query: str) -> dict:
  async def _handle_file_search(self, query: str) -> dict:
  async def _handle_system_query(self) -> dict:
  ```

### Step 4: Update Interactive Mode

- [ ] Find `async def interactive_mode(self):` (~line 578)
- [ ] Replace the `_should_chat` logic with:
  ```python
  result = await self.process_with_intent(
      user_input,
      context={"chat_mode": self.chat_mode}
  )
  ```

- [ ] Add result handling:
  ```python
  result_type = result.get("type")
  if result_type == "text":
      # Display text response
  elif result_type == "command_approval":
      # Show command and ask for approval
  # ... etc
  ```

### Step 5: Test CLI

- [ ] Start services: `make start-all`
- [ ] Run CLI: `aish`
- [ ] Test cases:
  ```
  > hello
  > what is docker?
  > how do I find large files?
  > show me large files
  > search the web for python
  ```
- [ ] Verify behavior matches expectations

## Phase 2: Voice Assistant Integration

### Step 1: Update Assistant Command

- [ ] Find `async def assistant(...)` (~line 2551)
- [ ] Remove the brittle `is_command_request` logic (~line 2690)
- [ ] Replace with:
  ```python
  result = await shell.process_with_intent(
      user_text,
      context={"voice_mode": True}
  )
  ```

### Step 2: Handle Results

- [ ] Add result type handling:
  ```python
  if result_type == "text":
      # Speak response directly
  elif result_type == "command_approval":
      # Ask for voice approval
  ```

### Step 3: Test Voice

- [ ] Run: `aish assistant -c`
- [ ] Test cases:
  ```
  "hello"
  "what is docker?"
  "can you show me how SSH works?"  # Should NOT say "I'll run..."
  "show me large files"  # Should say "I'll run..."
  ```

## Phase 3: Overlay Integration

### Step 1: Update Handle Query

- [ ] Find `async def handle_query(text: str):` in overlay command (~line 1604)
- [ ] Replace ad-hoc routing (line 2174) with:
  ```python
  result = await shell.process_with_intent(
      text,
      context={
          "chat_mode": state.get("chat_mode", False),
          "active_app": state.get("active_app")
      }
  )
  ```

### Step 2: Add Result Rendering

- [ ] Handle different result types for overlay:
  ```python
  if result_type == "text":
      return content
  elif result_type == "command_approval":
      state["pending"] = {...}
      return "Command ready: ..."
  elif result_type == "search_results":
      return {"_overlay_render": "...", ...}
  ```

### Step 3: Fix Web Search

- [ ] Ensure pending actions are stored in `state["pending"]`
- [ ] Verify approval buttons trigger pending actions
- [ ] Test: Type "/web python tutorials" → click result → browser opens

### Step 4: Test Overlay

- [ ] Start: `aish overlay --hotkey --tray`
- [ ] Test cases:
  ```
  "hello"
  "what is docker?"
  "how do I find large files?"
  "show me large files"
  "/web python tutorials"
  ```
- [ ] Verify web search opens browser

## Phase 4: Polish and Testing

### Comprehensive Testing

- [ ] **Greetings** (should not ask for approval)
  - "hello", "hi", "hey", "how are you?"
  
- [ ] **Informational** (should explain, not run)
  - "what is X?", "explain Y", "tell me about Z"
  
- [ ] **How-to** (should teach, not execute)
  - "how do I find files?", "show me how to use grep"
  
- [ ] **Commands** (should ask for approval)
  - "show me large files", "list processes", "find python files"
  
- [ ] **Web search** (should show results + approval)
  - "search web for X", "google Y"
  - In CLI: displays results, asks to open
  - In overlay: displays results, button opens browser
  - In voice: announces results, asks to open
  
- [ ] **File search** (should show results + approval)
  - "find documents about X", "search files containing Y"

### Edge Cases

- [ ] Empty input
- [ ] Very long input
- [ ] Special characters
- [ ] Multiple intents in one sentence
- [ ] Ambiguous inputs

### Performance

- [ ] Check logs for intent classification times
- [ ] Verify < 500ms end-to-end response
- [ ] Monitor LLM call frequency

## Phase 5: Monitoring and Iteration

### Add Logging

- [ ] Ensure intent classification is logged:
  ```python
  logger.info(
      "Intent classified",
      intent=result["intent"],
      confidence=result["confidence"],
      input=user_input[:50]
  )
  ```

### Monitor Metrics

- [ ] Track false positives (commands for greetings)
- [ ] Track false negatives (no approval when needed)
- [ ] User feedback on natural behavior

### Iterate on Prompts

If accuracy is low:
- [ ] Review logged reasoning
- [ ] Adjust system prompts in `intent_handlers.py`
- [ ] Add more heuristics in `intent.py`
- [ ] Adjust confidence thresholds

## Optional: LangChain Integration (Future)

If you want multi-agent capabilities:

- [ ] Add dependencies:
  ```bash
  pip install langchain langchain-community
  ```

- [ ] Review LangChain section in `AGENT_INTELLIGENCE_ANALYSIS.md`
- [ ] Implement agent system
- [ ] Create specialized agents
- [ ] Add agent tools
- [ ] Test agent coordination

## Rollback Plan (If Needed)

If issues arise:

- [ ] **Option 1**: Disable LLM classification
  ```bash
  export INTENT_USE_LLM=false
  ```

- [ ] **Option 2**: Disable intent system entirely
  ```bash
  export DISABLE_INTENT_SYSTEM=true
  ```

- [ ] **Option 3**: Git revert
  ```bash
  git stash  # Save your changes
  git revert HEAD  # Revert last commit
  ```

## Success Criteria

✅ **Functionality**
- Greetings get friendly responses (no approval)
- Questions get explanations (no commands)
- How-to gets instructions (no execution)
- Commands get approval consistently
- Web search opens browser everywhere

✅ **Performance**
- Response time < 500ms (acceptable)
- No noticeable lag
- LLM calls are reasonable

✅ **User Experience**
- Natural behavior
- Consistent across interfaces
- No confusion
- Reduced false positives

✅ **Technical**
- No new linting errors
- Logs show correct classification
- Tests pass
- Code is maintainable

## Timeline Estimate

- **Phase 1** (CLI): 2-4 hours
- **Phase 2** (Voice): 1-2 hours
- **Phase 3** (Overlay): 2-3 hours
- **Phase 4** (Testing): 2-3 hours
- **Total**: 7-12 hours (1-2 days)

## Help and Support

If you get stuck:

1. **Check the docs**:
   - `INTEGRATION_GUIDE.md` has code examples
   - `AGENT_INTELLIGENCE_ANALYSIS.md` has architecture details

2. **Test standalone**:
   ```bash
   python test_intent_system.py --interactive
   ```

3. **Check logs**:
   - Look for "Intent classified" log messages
   - Review confidence scores and reasoning

4. **Try heuristics only**:
   ```bash
   export INTENT_USE_LLM=false
   ```

5. **Ask for help**: Review error messages, check what intent was classified

## Completion Checklist

Once everything is working:

- [ ] All test cases pass
- [ ] CLI, voice, and overlay work correctly
- [ ] Web search opens browser consistently
- [ ] No false "I'll run..." in voice
- [ ] Greetings are natural
- [ ] Commands get proper approval
- [ ] Performance is acceptable
- [ ] User experience is improved
- [ ] Documentation is updated (if needed)
- [ ] Consider committing changes

## Next Steps After Implementation

1. **Gather user feedback** (2-4 weeks)
2. **Monitor logs** for misclassifications
3. **Tune prompts** if needed
4. **Consider LangChain** if multi-agent features desired
5. **Expand intent types** (if new use cases emerge)

---

**You're ready to start! Begin with Phase 1 (CLI integration) and test thoroughly before moving to the next phase.**

Good luck! 🚀

