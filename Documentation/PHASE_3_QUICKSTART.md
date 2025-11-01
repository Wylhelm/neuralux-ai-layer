# Phase 3 Quick Start Guide

Get started with Neuralux's proactive intelligence features in 5 minutes!

## What You Get

Three new background services that work together:

- 🕐 **Temporal** - Remembers what you do
- 🤖 **Agent** - Suggests helpful next steps
- ⚙️ **System** - Takes action when you approve

## 1. Check Status

```bash
aish status
```

**Look for these three Phase 3 services:**
```
✓ Temporal service: Running
✓ Agent service: Running  
✓ System service: Running
```

**If not running, start them:**
```bash
make start-all
```

**Verify services are working:**
```bash
# Check temporal service is recording events
tail -f data/logs/temporal-service.log

# Check agent service is detecting patterns
tail -f data/logs/agent-service.log

# Check system service is ready for actions
tail -f data/logs/system-service.log
```

## 2. Try It Now

### Test 1: Git Clone Assistant

```bash
aish
> "git clone https://github.com/torvalds/linux.git"
```

**Expected**: Desktop notification asking if you want to inspect dependencies!

### Test 2: View Your Timeline

```bash
python tests/query_timeline.py command --limit 5
```

**Expected**: Shows your recent commands with timestamps.

### Test 3: Force a Notification

```bash
python tests/test_proactive_agent.py
```

**Expected**: Immediate desktop notification with a test suggestion.

## 3. How It Works

```
You run a command
       ↓
Temporal records it
       ↓
Agent analyzes pattern
       ↓
Desktop notification with suggestions
       ↓
You click action button
       ↓
System executes it
```

## Common Patterns

### Git Clone
```bash
> "git clone https://github.com/user/repo.git"
```
**Suggests**: Inspect dependencies, install packages

### High Disk Usage
Detected automatically every 5 minutes.

**Suggests**: Find large files, clean caches

### Build Complete
```bash
> "npm run build"
```
**Suggests**: Deploy, test, share

### Docker Start
```bash
> "docker-compose up -d"
```
**Suggests**: View logs, check status, open web UI

## View Your Activity

```bash
# Recent commands
python tests/query_timeline.py command

# File changes
python tests/query_timeline.py file

# System snapshots
python tests/query_timeline.py system_snapshot

# Everything (last 20)
python tests/query_timeline.py all --limit 20
```

## Troubleshooting

### No Notifications?

Test if notify-send works:
```bash
notify-send "Test" "You should see this!"
```

If nothing appears:
```bash
sudo apt install libnotify-bin
```

### Services Not Running?

Check logs:
```bash
tail -f data/logs/temporal-service.log
tail -f data/logs/agent-service.log
tail -f data/logs/system-service.log
```

Restart services:
```bash
make stop-all
make start-all
```

### Timeline Empty?

Commands must go through `aish`:
```bash
# ✅ Tracked
aish
> "ls -la"

# ❌ Not tracked
ls -la  # (direct shell command)
```

## Configuration

### Change Watched Directories

Edit `services/temporal/config.py`:
```python
WATCH_PATHS = [
    "~/Documents",
    "~/Projects",    # Your projects
    "~/Downloads"
]
```

### Add Custom Patterns

Edit `services/agent/patterns.py` and add your pattern class. See [Examples](PHASE_3_EXAMPLES.md#custom-patterns).

### Adjust Snapshot Interval

Edit `services/temporal/config.py`:
```python
SNAPSHOT_INTERVAL = 300  # seconds (default: 5 minutes)
```

## What's Next?

1. ✅ Use `aish` for your daily commands
2. ✅ Watch for helpful notifications
3. ✅ Create custom patterns for your workflow
4. ✅ Share patterns with the community

## Learn More

- **[User Guide](PHASE_3_USER_GUIDE.md)** - Complete documentation
- **[Architecture](PHASE_3_ARCHITECTURE.md)** - Technical deep dive
- **[Examples](PHASE_3_EXAMPLES.md)** - 17 practical examples
- **[Implementation](PHASE_3_IMPLEMENTATION.md)** - Developer guide

## Quick Commands Cheat Sheet

```bash
# Status
aish status

# View timeline
python tests/query_timeline.py all

# Test notification
python tests/test_proactive_agent.py

# Check logs
tail -f data/logs/agent-service.log

# Restart services
make stop-all && make start-all

# Clear timeline
rm -f data/temporal/timeline.duckdb*
```

## Example Session

```bash
# Start AI shell
aish

# Clone a repository
> "git clone https://github.com/awesome/project.git"

🔔 Notification: "New Project Detected - Inspect for dependencies?"
[Click: Yes, inspect]

🔔 Notification: "Found package.json - Install dependencies?"
[Click: npm install]

# Installation happens automatically
✅ Dependencies installed!

# Continue working
> "npm run dev"

🔔 Notification: "Dev server starting - Open in browser?"
[Click: Open browser]

# Browser opens to http://localhost:3000
✅ You're up and running!
```

**All of this was automated with Phase 3!** 🚀

## Privacy Note

- ✅ All data stored locally in `data/temporal/timeline.duckdb`
- ✅ Nothing sent to cloud
- ✅ You can view/delete all data anytime
- ✅ Only your user has access

Clear your timeline:
```bash
rm -f data/temporal/timeline.duckdb*
```

---

**Ready to experience proactive AI assistance?**

Start using `aish` for your commands and let Neuralux help you! 🎉

