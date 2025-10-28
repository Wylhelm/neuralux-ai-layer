# Overlay Conversational Enhancement Plan

**Status**: 📋 Planning  
**Target**: Phase 2A Enhancement  
**Dependencies**: Conversational Intelligence System (✅ Complete)

## Overview

This document outlines the plan to enhance the GUI overlay with the conversational intelligence system, bringing the same natural, multi-step workflow capabilities that are currently available in the CLI (`aish converse`) to the graphical interface.

## Current State

### What We Have (CLI)
✅ Conversational mode with full features:
- Multi-step workflow planning
- Contextual memory across turns
- Reference resolution ("it", "that file", "the image")
- Action chaining (outputs feed into next action)
- Batch approval for multi-step workflows
- Command execution with stdin support
- Document query integration
- Web search integration
- Beautiful terminal output with tables

### What We Have (Overlay)
✅ Basic GUI overlay features:
- Global hotkey (Alt+Space)
- Fuzzy search
- LLM integration (single-turn)
- Voice controls (mic/speaker)
- OCR with action buttons
- Image generation
- Web search (basic)
- System tray
- Session memory (basic)

### Gap Analysis
The overlay currently lacks:
- ❌ Full conversation history view
- ❌ Action planning and approval UI
- ❌ Multi-step workflow visualization
- ❌ Context variable display
- ❌ Reference resolution feedback
- ❌ Document query results display
- ❌ Command execution approval
- ❌ Action result cards
- ❌ Session management UI

## Enhancement Architecture

### Component Integration

```
┌─────────────────────────────────────────────┐
│         Overlay Window (GTK4)               │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   Conversation History Panel         │  │
│  │   - Scrollable message list          │  │
│  │   - Action cards with results        │  │
│  │   - Context indicators               │  │
│  │   - Inline approvals                 │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   Input Area                         │  │
│  │   - Text entry with suggestions      │  │
│  │   - Voice input button               │  │
│  │   - Quick action buttons             │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   Context Sidebar (collapsible)      │  │
│  │   - Variables                        │  │
│  │   - Last actions                     │  │
│  │   - Session info                     │  │
│  └──────────────────────────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

### Integration Points

1. **ConversationHandler Integration**
   - Replace current single-turn LLM calls
   - Wire to existing message bus client
   - Share session ID with CLI mode

2. **Action Approval UI**
   - Modal dialog for multi-step approvals
   - Show planned actions with details
   - Allow selective approval

3. **Result Display**
   - Rich action cards for each result
   - Inline document query results
   - Web search results in tables
   - Command output in expandable sections

4. **Context Display**
   - Sidebar showing active variables
   - Visual indicators for references
   - Last action breadcrumbs

## Implementation Phases

### Phase 1: Core Integration (Week 1)

**Goal**: Get basic conversational mode working in overlay

**Tasks**:
1. Create `overlay_conversation_handler.py`
   - Wrapper around `ConversationHandler`
   - GTK-friendly async handling
   - Session management

2. Modify `overlay_window.py`
   - Replace single-turn LLM with conversation handler
   - Add conversation history storage
   - Wire up existing UI to new handler

3. Basic message display
   - Show user/assistant messages
   - Display simple text responses
   - Handle errors gracefully

**Deliverables**:
- Messages persist in UI
- Multi-turn conversations work
- Context maintained across turns

### Phase 2: Action Planning UI (Week 2)

**Goal**: Show planned actions and get approval

**Tasks**:
1. Create action approval dialog
   - Modal window showing action list
   - Checkbox for each action (optional selective approval)
   - Parameter display for transparency
   - Approve/Cancel buttons

2. Action visualization
   - Icons for action types
   - Color coding (needs approval vs automatic)
   - Parameter preview
   - Dependency indicators

3. Wire approval flow
   - Hook into ConversationHandler approval system
   - Handle user approval/cancellation
   - Show execution progress

**Deliverables**:
- Users see what will happen before approval
- Can approve or cancel workflows
- Clear visual feedback

### Phase 3: Result Cards (Week 3)

**Goal**: Beautiful display of action results

**Tasks**:
1. Create result card components
   - Command output card (stdout/stderr)
   - Document query result card (table view)
   - Web search result card (links)
   - Image generation card (preview)
   - File operation card (path + status)

2. Implement card rendering
   - Add to conversation history
   - Expandable/collapsible sections
   - Copy buttons for useful content
   - Quick actions (open, save, etc.)

3. Handle special cases
   - Large outputs (truncation)
   - Binary files
   - Errors vs successes

**Deliverables**:
- Rich display of all action types
- Interactive result cards
- Better UX than CLI

### Phase 4: Conversation History (Week 4)

**Goal**: Full scrollable conversation with persistence

**Tasks**:
1. Conversation list widget
   - Scrollable message container
   - User/assistant alternating layout
   - Action cards inline
   - Timestamp display

2. History management
   - Load previous conversation on startup
   - Scroll to bottom on new message
   - Keyboard navigation
   - Search/filter capability

3. Session controls
   - New conversation button
   - Reset context button
   - Save conversation
   - Export conversation

**Deliverables**:
- Full conversation visible
- Can scroll through history
- Session management

### Phase 5: Context Visualization (Week 5)

**Goal**: Show what the AI remembers

**Tasks**:
1. Context sidebar
   - Collapsible panel
   - Variable list
   - Last action summary
   - Reference indicators

2. Visual feedback
   - Highlight when reference resolved
   - Show which file/image is "it"
   - Display active context

3. Context controls
   - Clear individual variables
   - View full context
   - Edit variables (advanced)

**Deliverables**:
- Visible context state
- Understanding of AI memory
- Control over context

### Phase 6: Polish & Features (Week 6)

**Goal**: Match and exceed CLI experience

**Tasks**:
1. Enhanced displays
   - Document query with thumbnails
   - Web search with favicons
   - Image gallery for generated images
   - Syntax highlighting for code

2. Quick actions
   - One-click approval shortcuts
   - Common workflow templates
   - Recent actions menu
   - Favorites

3. Settings integration
   - Configure approval preferences
   - Auto-approve trusted actions
   - Customize displays

**Deliverables**:
- Polished experience
- Power user features
- Better than CLI

## UI Components Specifications

### 1. Message Bubble Component

```python
class MessageBubble(Gtk.Box):
    """Display a single conversation message."""
    
    def __init__(self, role: str, content: str, timestamp: float):
        # Role: "user" or "assistant"
        # Visual distinction (color, alignment)
        # Timestamp display
        # Copy button
```

**Visual**:
- User: Right-aligned, blue background
- Assistant: Left-aligned, gray background
- Timestamp in corner (subtle)
- Markdown rendering for content

### 2. Action Card Component

```python
class ActionCard(Gtk.Box):
    """Display an action result with details."""
    
    def __init__(self, action: dict):
        # Action type icon
        # Description
        # Status indicator
        # Details section (expandable)
        # Quick actions (copy, open, etc.)
```

**Types**:
- **Command Output**: Show stdout/stderr with syntax highlighting
- **Document Query**: Table of results with open buttons
- **Web Search**: Clickable links with previews
- **Image**: Thumbnail with save/copy buttons
- **LLM Generate**: Text with copy button

### 3. Approval Dialog Component

```python
class ApprovalDialog(Gtk.Dialog):
    """Modal dialog for action approval."""
    
    def __init__(self, actions: List[Action], explanation: str):
        # Title: explanation
        # List of actions with checkboxes
        # Parameter display for each
        # Approve All / Approve Selected / Cancel buttons
```

**Features**:
- Show exact commands that will execute
- Parameter values visible
- Selective approval (check/uncheck)
- Preview mode (show without executing)

### 4. Context Sidebar Component

```python
class ContextSidebar(Gtk.Box):
    """Collapsible sidebar showing context."""
    
    def __init__(self, context: ConversationContext):
        # Variables section
        # Last action section
        # Reference indicators
        # Session info
```

**Features**:
- Collapse/expand button
- Variable names with values
- Click to copy
- Visual indicators for "hot" variables

### 5. Document Result Card

```python
class DocumentResultCard(Gtk.Box):
    """Display document query results."""
    
    def __init__(self, results: List[dict], query: str):
        # Header: "Found N documents"
        # Table/list of results
        # Open buttons for each
        # Relevance scores
```

**Features**:
- Numbered list (1-10)
- File icons by type
- Quick open button
- Preview on hover

### 6. Web Result Card

```python
class WebResultCard(Gtk.Box):
    """Display web search results."""
    
    def __init__(self, results: List[dict], query: str):
        # Header: "Found N results"
        # List of links
        # Snippets
        # Open buttons
```

**Features**:
- Numbered links
- Favicon display
- Open in browser button
- Copy URL button

## Technical Implementation Details

### File Structure

```
packages/overlay/
├── __init__.py
├── overlay_window.py              (Modified)
├── config.py
├── hotkey.py
├── search.py
├── tray.py
├── tray_helper.py
│
├── conversation/                   (New)
│   ├── __init__.py
│   ├── handler.py                 # Overlay-specific conversation handler
│   ├── history_widget.py          # Scrollable conversation view
│   ├── message_bubble.py          # User/assistant message display
│   ├── action_card.py             # Action result cards
│   ├── approval_dialog.py         # Approval modal
│   ├── context_sidebar.py         # Context variable display
│   └── result_cards/              # Specialized result displays
│       ├── __init__.py
│       ├── command_card.py
│       ├── document_card.py
│       ├── web_card.py
│       ├── image_card.py
│       └── llm_card.py
│
└── styles/                        (New)
    └── conversation.css           # GTK CSS for styling
```

### Key Changes to overlay_window.py

```python
class OverlayWindow(Gtk.ApplicationWindow):
    def __init__(self, ...):
        # ... existing code ...
        
        # NEW: Conversation handler
        self.conversation_handler = None
        self.conversation_history = []
        
        # NEW: UI components
        self._setup_conversation_ui()
    
    def _setup_conversation_ui(self):
        """Setup conversation history and cards."""
        # Create scrollable conversation view
        self.conversation_view = ConversationHistoryWidget()
        
        # Create context sidebar
        self.context_sidebar = ContextSidebar()
        
        # Wire up to main layout
        # ... layout code ...
    
    async def _handle_user_input(self, text: str):
        """Process user input through conversation handler."""
        # Replace current single-turn logic
        
        # Show user message immediately
        self.conversation_view.add_message("user", text)
        
        # Process with conversation handler
        result = await self.conversation_handler.process_message(text)
        
        if result["type"] == "needs_approval":
            # Show approval dialog
            approved = self._show_approval_dialog(result)
            if approved:
                result = await self.conversation_handler.approve_and_execute(...)
        
        # Display results
        self._display_result(result)
```

### Data Flow

```
User Input
    ↓
Overlay Window
    ↓
ConversationHandler.process_message()
    ↓
ActionPlanner.plan_actions()
    ↓
[Approval Dialog] ← If actions need approval
    ↓
ActionOrchestrator.execute_action() × N
    ↓
Results back to Overlay
    ↓
Render Action Cards
    ↓
Update Context Sidebar
    ↓
Update Conversation View
```

## Styling Guidelines

### Color Scheme

```css
/* User messages */
.message-user {
    background: #2196F3;
    color: white;
    border-radius: 12px 12px 4px 12px;
}

/* Assistant messages */
.message-assistant {
    background: #37474F;
    color: white;
    border-radius: 12px 12px 12px 4px;
}

/* Action cards */
.action-card {
    background: #424242;
    border: 1px solid #616161;
    border-radius: 8px;
    margin: 8px 0;
}

/* Approval needed */
.action-approval-needed {
    border-left: 4px solid #FF9800;
}

/* Action success */
.action-success {
    border-left: 4px solid #4CAF50;
}

/* Action failed */
.action-failed {
    border-left: 4px solid #F44336;
}

/* Context sidebar */
.context-sidebar {
    background: #263238;
    border-left: 1px solid #37474F;
}
```

### Layout Principles

1. **Conversation Flow**: Natural top-to-bottom timeline
2. **Visual Hierarchy**: User/assistant clearly distinguished
3. **Action Emphasis**: Cards stand out from messages
4. **Context Available**: Sidebar unobtrusive but accessible
5. **Mobile-Ready**: Future-proof for touch displays

## User Experience Enhancements

### Smart Defaults
- Auto-approve LLM/OCR/search (no filesystem impact)
- Always require approval for file operations
- Remember approval preferences per session

### Keyboard Shortcuts
- `Ctrl+Enter`: Send message
- `Ctrl+K`: Clear input
- `Ctrl+N`: New conversation
- `Ctrl+H`: Toggle history
- `Ctrl+B`: Toggle context sidebar
- `Escape`: Cancel/close

### Voice Integration
- Voice input appends to conversation
- TTS reads assistant responses
- Voice approval: "yes" / "no" / "approve"

### Accessibility
- Screen reader friendly
- High contrast mode
- Keyboard navigation
- Adjustable font sizes

## Migration Strategy

### Phase 1: Parallel Mode
- Keep existing single-turn mode
- Add "Conversational Mode" toggle
- Let users opt-in

### Phase 2: Default Conversational
- Make conversational mode default
- Keep simple mode as fallback
- Automatic detection

### Phase 3: Full Migration
- Remove legacy single-turn code
- Conversational mode only
- Clean up codebase

## Testing Plan

### Unit Tests
- [ ] ConversationHandler integration
- [ ] Action card rendering
- [ ] Approval dialog logic
- [ ] Context sidebar updates
- [ ] History persistence

### Integration Tests
- [ ] Full workflow: create file → write → image → save
- [ ] Multi-step approval flow
- [ ] Document query → open document
- [ ] Web search → open link
- [ ] Voice input → execution

### UI Tests
- [ ] Message rendering
- [ ] Card display
- [ ] Scrolling performance
- [ ] Context updates
- [ ] Keyboard navigation

### User Testing
- [ ] Beta testers try workflows
- [ ] Feedback on approval UX
- [ ] Performance with long conversations
- [ ] Compare with CLI experience

## Performance Considerations

### Optimization Targets
- Message rendering: <16ms per message (60fps)
- Action card creation: <50ms
- History load: <200ms for 100 messages
- Context updates: <10ms
- Memory: <100MB for full session

### Strategies
- Virtual scrolling for long conversations
- Lazy load action card details
- Cache rendered widgets
- Batch context updates
- Async everything

## Documentation Updates

### User Documentation
- [ ] Overlay conversational mode guide
- [ ] Action approval tutorial
- [ ] Context management guide
- [ ] Comparison with CLI mode

### Developer Documentation
- [ ] Architecture overview
- [ ] Component API reference
- [ ] Styling guidelines
- [ ] Extension points

## Success Metrics

### Functionality
- ✅ All CLI workflows work in overlay
- ✅ Approval UX is clear and fast
- ✅ Results display is informative
- ✅ Context is visible and useful

### Performance
- ✅ Smooth 60fps scrolling
- ✅ Fast action execution
- ✅ No UI freezes
- ✅ Memory stable

### User Satisfaction
- ✅ Preference: Overlay ≥ CLI
- ✅ Task completion faster
- ✅ Fewer errors
- ✅ Higher engagement

## Timeline Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 1. Core Integration | 1 week | Basic conversation works |
| 2. Action Planning UI | 1 week | Approval flow complete |
| 3. Result Cards | 1 week | Rich result display |
| 4. Conversation History | 1 week | Full scrollable view |
| 5. Context Visualization | 1 week | Sidebar complete |
| 6. Polish & Features | 1 week | Production ready |

**Total**: 6 weeks for complete overlay enhancement

## Dependencies

### External Libraries
- GTK4 (existing)
- Rich (for CLI fallback)
- Markdown renderer (GTK or external)

### Internal Components
- ✅ ConversationHandler (complete)
- ✅ ActionOrchestrator (complete)
- ✅ ActionPlanner (complete)
- ✅ ConversationContext (complete)

### Services
- ✅ LLM service
- ✅ Vision service
- ✅ Filesystem service (with write ops)
- ✅ Audio service

## Risk Assessment

### Technical Risks
- **GTK async complexity**: Medium
  - Mitigation: Use GLib async primitives
  
- **UI performance**: Medium
  - Mitigation: Virtual scrolling, lazy loading
  
- **State synchronization**: Low
  - Mitigation: Redis-backed context (already working)

### UX Risks
- **Approval fatigue**: Medium
  - Mitigation: Smart defaults, batch approval
  
- **Information overload**: Low
  - Mitigation: Progressive disclosure, collapsible sections

### Schedule Risks
- **Scope creep**: Medium
  - Mitigation: Phased approach, MVP first

## Future Enhancements

### Post-MVP Features
- **Workflow Templates**: Save common workflows
- **Macros**: Record and replay action sequences
- **Collaboration**: Share conversations
- **History Search**: Find past conversations
- **Export**: Save conversations to file
- **Themes**: Customizable appearance
- **Plugins**: Extension system for custom cards

### Advanced Features
- **Multi-modal Input**: Drag-drop images into conversation
- **Voice-First Mode**: Fully voice-controlled
- **Gesture Controls**: Touch/trackpad gestures
- **Split View**: Multiple conversations side-by-side
- **Cloud Sync**: Sync conversations across devices

## Conclusion

This enhancement will bring the powerful conversational intelligence system to the GUI overlay, making it the **primary interface** for Neuralux. The phased approach ensures we deliver value early while building toward a polished, feature-rich experience that exceeds the CLI capabilities.

The key is maintaining the **natural, fluid conversation** feel while leveraging GUI advantages like rich displays, interactive approvals, and visual context.

**Next Step**: Begin Phase 1 implementation - Core Integration.

