# Phase 3: Proactive Intelligence User Guide

Welcome to Neuralux Phase 3! This guide explains the new proactive features and how to use them.

## What's New in Phase 3?

Phase 3 introduces **proactive intelligence** - your system now learns from your activities and offers contextual assistance. Three new services work together to make this happen:

### 🕐 **Temporal Service** - Your System's Memory
Records a private, local timeline of your activities:
- Commands you execute
- Files you create/modify
- Applications you use
- System state snapshots

**Privacy First**: All data stays local. Nothing is sent to the cloud.

### 🤖 **Agent Service** - Your Proactive Assistant
Analyzes the timeline in real-time and offers helpful suggestions:
- Detects patterns in your workflow
- Sends desktop notifications with contextual help
- Suggests next steps based on what you're doing

### ⚙️ **System Service** - System Control
Allows AI to perform safe system actions on your behalf:
- List running processes
- Manage system resources
- Execute approved automation tasks

---

## Getting Started

### Check Service Status

First, verify all services are running:

```bash
aish status
```

You should see:
```
✓ LLM service: Running
✓ Filesystem service: Running
✓ Health service: Running
✓ Audio service: Running
✓ Vision service: Running
✓ Temporal service: Running      ← New!
✓ Agent service: Running         ← New!
✓ System service: Running        ← New!
```

### Start All Services

If services aren't running:

```bash
# Start all infrastructure and services
make start-all
```

---

## Using Proactive Features

### Automatic Command Tracking

**What happens**: Every command you run in `aish` is automatically recorded by the Temporal Service.

**Try it:**

```bash
# Start the AI shell
aish

# Run any command - it's automatically tracked
> "show me large files in downloads"
```

The command execution is:
1. **Recorded** by the Temporal Service
2. **Analyzed** by the Agent Service
3. **May trigger** a helpful notification

### Desktop Notifications

**What happens**: When the Agent detects a useful pattern, you'll get a desktop notification with suggestions.

**Example - Git Clone Pattern**:

```bash
# Clone a repository
> "git clone https://github.com/some/cool-project.git"
```

**You'll receive a notification:**
```
🔔 Neuralux Agent
New Project Detected

You just cloned 'cool-project'. Would you like me to 
inspect it for a 'requirements.txt' or 'package.json' 
to install dependencies?

[Yes, inspect]  [No, thanks]
```

### AI-Powered Suggestions

Beyond specific patterns, the Agent uses your LLM to suggest contextual follow-ups:

```bash
# Run a command that creates files
> "generate report.pdf from data.csv"
```

**Possible notification:**
```
🔔 Neuralux Agent
Suggestion

You just created report.pdf. Would you like to:
• Preview the PDF
• Email it to someone
• Archive with timestamp

[Show suggestions]
```

---

## Viewing Your Timeline

### Query Timeline Database

The Temporal Service stores events in a DuckDB database. View them using:

```bash
# View all recent events (last 10)
python tests/query_timeline.py

# View only command events
python tests/query_timeline.py command

# View specific event types
python tests/query_timeline.py file           # File changes
python tests/query_timeline.py app_focus      # App switches
python tests/query_timeline.py system_snapshot # System states

# Show more events (e.g., last 50)
python tests/query_timeline.py all --limit 50
```

**Example output:**
```
🔎 Querying timeline database: data/temporal/timeline.duckdb

--- Contents of command_events (last 10 entries) ---
  event_id                              timestamp             command                        exit_code  cwd
  a1b2c3...  2025-10-31 10:23:45.123  git clone https://...  0          /home/user/Projects
  d4e5f6...  2025-10-31 10:20:12.456  ls -la                 0          /home/user
```

### Timeline Data Location

All timeline data is stored locally:
- **Database**: `data/temporal/timeline.duckdb`
- **Event types**:
  - `command_events` - Commands you execute
  - `file_events` - File system changes
  - `app_focus_events` - Application switches
  - `system_snapshot_events` - Periodic system state

---

## Using System Control Features

### Via CLI (for testing)

Test system control actions:

```bash
# Test the system service
python tests/test_system_service.py
```

This demonstrates:
- Listing all running processes
- Attempting to terminate a process (safely fails for non-existent PID)

### Via NATS API

Services can request system actions via NATS:

```python
import asyncio
import json
from nats.aio.client import Client as NATS

async def list_processes():
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    
    # Request process list
    response = await nc.request("system.action.process.list", b'', timeout=5.0)
    data = json.loads(response.data.decode())
    
    if data["status"] == "success":
        for proc in data["data"]:
            print(f"PID {proc['pid']}: {proc['name']}")
    
    await nc.close()

asyncio.run(list_processes())
```

**Available Actions:**
- `system.action.process.list` - List running processes
- `system.action.process.kill` - Terminate a process (requires PID)

**Future actions** (planned):
- System updates
- Package management
- Service control
- Resource management

---

## GUI Integration

### Current Overlay Features

The overlay currently subscribes to agent suggestions but doesn't display them yet. This is **planned for Phase 4**.

**What works now:**

1. **Conversation Mode** - Multi-step workflows with memory
   ```bash
   # Launch overlay
   aish overlay --hotkey --tray
   
   # Try: "create a file named test.txt and write hello world in it"
   # The conversation handler uses contextual memory like the temporal service
   ```

2. **Voice Commands** - Tracked and analyzed
   - Voice commands go through the temporal service
   - Agent can suggest follow-ups based on voice interactions

**Coming in Phase 4:**

- Notification panel in overlay
- Accept/dismiss suggestions in GUI
- Visual timeline browser
- Proactive suggestions overlay

### Check Agent Activity

Monitor what the agent is detecting:

```bash
# View agent service logs
tail -f data/logs/agent-service.log
```

You'll see:
- Events being processed
- Patterns matched
- Suggestions generated
- Notifications sent

---

## Testing Proactive Features

### Manual Testing

Test the git clone pattern:

```bash
# Publish a fake git clone event
python tests/test_proactive_agent.py
```

**Expected result:**
```
🚀 Publishing a fake 'git clone' event to test the proactive agent...
✅ Event published successfully.
👀 Check your desktop notifications for a suggestion from the Neuralux Agent.
```

You should receive a desktop notification about the cloned repository.

### Custom Event Testing

Send custom command events:

```python
#!/usr/bin/env python3
import asyncio
import json
from nats.aio.client import Client as NATS

async def send_custom_event():
    nc = NATS()
    await nc.connect("nats://localhost:4222")
    
    # Create a custom command event
    event = {
        "event_type": "command",
        "command": "docker-compose up -d",  # Your command
        "cwd": "/home/user/project",
        "exit_code": 0,
        "user": "user"
    }
    
    # Send to temporal service
    await nc.publish("temporal.command.new", json.dumps(event).encode())
    print("✅ Event sent! Check for agent notifications.")
    
    await nc.close()

asyncio.run(send_custom_event())
```

---

## Configuration

### Temporal Service

Edit `services/temporal/config.py`:

```python
# Monitoring settings
SNAPSHOT_INTERVAL = 300  # System snapshot every 5 minutes
WATCH_PATHS = [          # Directories to monitor
    "~/Documents",
    "~/Projects",
    "~/Downloads"
]

# Database
DB_PATH = "data/temporal/timeline.duckdb"
```

### Agent Service

Edit `services/agent/config.py`:

```python
# Event stream
EVENT_STREAM_SUBJECT = "temporal.event.>"  # Listen to all events

# LLM timeout for suggestions
LLM_TIMEOUT = 3.0  # seconds

# Notification settings (system level)
# Uses notify-send - configure via system settings
```

### System Service

Edit `services/system/config.py`:

```python
# Security settings
REQUIRE_APPROVAL = True  # Require approval for destructive actions
ALLOWED_ACTIONS = [       # Whitelist of allowed actions
    "process.list",
    "process.kill"
]
```

---

## Privacy & Security

### What's Collected

**Temporal Service collects locally:**
- ✅ Commands you execute (with context)
- ✅ Files you create/modify (paths only, not content)
- ✅ Active applications
- ✅ System metrics (CPU, memory, disk)

**NOT collected:**
- ❌ File contents
- ❌ Passwords or sensitive data
- ❌ Network traffic
- ❌ Browser history

### Data Retention

Default retention (can be customized):
- **Command events**: 30 days
- **File events**: 7 days
- **System snapshots**: 24 hours
- **App focus events**: 7 days

### Clearing Data

Delete your timeline:

```bash
# Stop services
make stop-all

# Remove timeline database
rm -f data/temporal/timeline.duckdb*

# Restart services
make start-all
```

### Disabling Tracking

Disable specific collectors in `services/temporal/config.py`:

```python
# Disable file system monitoring
ENABLE_FILESYSTEM_COLLECTOR = False

# Disable system snapshots
ENABLE_SNAPSHOT_COLLECTOR = False
```

Or stop the temporal service entirely:

```bash
# Stop just the temporal service
pkill -f "services/temporal/service.py"
```

---

## Troubleshooting

### No Notifications Appearing

**Check if notify-send works:**
```bash
notify-send "Test" "If you see this, notifications work!"
```

**If no notification appears:**
- Install libnotify: `sudo apt install libnotify-bin`
- Check notification settings in your desktop environment

**Check agent service logs:**
```bash
tail -f data/logs/agent-service.log
```

### Services Not Starting

**Check service status:**
```bash
aish status
```

**Check individual service logs:**
```bash
tail -f data/logs/temporal-service.log
tail -f data/logs/agent-service.log
tail -f data/logs/system-service.log
```

**Common issues:**
- NATS not running: `make start` (infrastructure)
- Python dependencies: `pip install -r requirements.txt`
- Permission issues: Check file ownership in `data/` directory

### Timeline Database Issues

**Database locked:**
```bash
# Stop services accessing it
make stop-all

# Remove write-ahead log
rm data/temporal/timeline.duckdb.wal

# Restart
make start-all
```

**Corrupted database:**
```bash
# Backup if needed
cp data/temporal/timeline.duckdb data/temporal/timeline.duckdb.backup

# Remove and recreate
rm data/temporal/timeline.duckdb*
make start-all
```

### Agent Not Suggesting

**Possible causes:**

1. **LLM service down**
   ```bash
   aish status  # Check LLM service
   ```

2. **Low confidence threshold**
   - Agent only suggests when confident
   - Check logs for "Pattern matched" or "Suggestion generated"

3. **Pattern not matching**
   - Current patterns: `git clone`
   - AI suggestions for other commands (may be sparse)

---

## Advanced Usage

### Creating Custom Patterns

Add your own detection patterns in `services/agent/patterns.py`:

```python
class NpmInstallPattern:
    """Detects when user runs npm install."""
    
    def process_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if event_data.get("event_type") != "command":
            return None
        
        command = event_data.get("command", "")
        
        # Detect npm install
        if "npm install" in command or "npm i" in command:
            return {
                "id": "npm_install_detected",
                "title": "Dependencies Installing",
                "message": "Would you like me to run the dev server when installation completes?",
                "actions": [
                    {"label": "Yes, start dev server", "command": "npm run dev"},
                    {"label": "No, thanks", "command": "ignore"}
                ]
            }
        
        return None

# Register the pattern
class PatternMatcher:
    def __init__(self, suggestion_engine=None):
        self.patterns = [
            GitClonePattern(),
            NpmInstallPattern(),  # Add your pattern
        ]
        self.suggestion_engine = suggestion_engine
```

### Integrating with Other Services

Use temporal events in your own services:

```python
# Subscribe to all events
await nc.subscribe("temporal.event.>", cb=your_handler)

# Subscribe to specific event types
await nc.subscribe("temporal.event.command", cb=command_handler)
await nc.subscribe("temporal.event.file", cb=file_handler)
```

### Building Automation Workflows

Combine system actions with temporal intelligence:

```python
async def auto_cleanup_workflow():
    """Example: Auto-cleanup when disk is full."""
    
    # Listen for system snapshots
    async def snapshot_handler(msg):
        data = json.loads(msg.data.decode())
        
        # Check disk usage
        if data.get("disk_usage_percent", 0) > 90:
            # Get large temporary files
            response = await nc.request(
                "system.file.search",
                {"path": "/tmp", "size": ">100MB"}
            )
            
            # Notify user
            await nc.publish("agent.notification", {
                "title": "Disk Almost Full",
                "message": "Found large temp files. Clean them up?",
                "actions": [
                    {"label": "Clean temp files", "command": "cleanup_temp"}
                ]
            })
    
    await nc.subscribe("temporal.event.system_snapshot", cb=snapshot_handler)
```

---

## What's Next?

### Phase 4 Preview

Planned features for the next phase:

- **🖥️ GUI Notification Panel**
  - Visual notification center in overlay
  - Accept/dismiss suggestions with one click
  - Notification history

- **📊 Timeline Visualization**
  - Browse your activity timeline
  - Filter by type/date
  - Search historical events

- **🎯 Smart Suggestions**
  - More sophisticated pattern detection
  - Context-aware recommendations
  - Learning from user preferences

- **🔗 Workflow Automation**
  - Chain system actions
  - Conditional automation
  - Scheduled tasks

### Feedback Welcome!

Try the proactive features and let us know:
- What patterns would you like detected?
- What suggestions would be helpful?
- How should the GUI display notifications?

---

## Quick Reference

### Service Ports

- **Temporal Service**: http://localhost:8007
- **Agent Service**: http://localhost:8008
- **System Service**: http://localhost:8009

### NATS Subjects

**Temporal Service:**
- `temporal.command.new` - Submit command events
- `temporal.event.command` - Command event stream
- `temporal.event.file` - File event stream
- `temporal.event.app_focus` - App focus stream
- `temporal.event.system_snapshot` - System snapshot stream

**Agent Service:**
- `agent.suggestion` - Suggestion notifications

**System Service:**
- `system.action.process.list` - List processes
- `system.action.process.kill` - Kill process

### Logs

- `data/logs/temporal-service.log`
- `data/logs/agent-service.log`
- `data/logs/system-service.log`

### Data Locations

- Timeline: `data/temporal/timeline.duckdb`
- PID files: `data/run/*.pid`

---

## Summary

**Phase 3 brings proactive intelligence to Neuralux:**

1. **Temporal Service** 🕐 - Records your system activity timeline
2. **Agent Service** 🤖 - Analyzes patterns and suggests next steps
3. **System Service** ⚙️ - Enables safe system automation

**Key Benefits:**
- ✅ Contextual help when you need it
- ✅ Learn from your workflow patterns
- ✅ Reduce repetitive tasks
- ✅ Private, local-first intelligence

**Try it now:**
```bash
# Check all services are running
aish status

# Try a git clone to see proactive suggestions
aish
> "git clone https://github.com/your/favorite-repo.git"

# Watch for the desktop notification! 🔔
```

Happy automating! 🚀

