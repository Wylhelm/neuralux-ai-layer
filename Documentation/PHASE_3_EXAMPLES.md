# Phase 3: Practical Examples & Use Cases

This guide shows real-world examples of how Phase 3's proactive intelligence works in practice.

## Table of Contents

1. [Development Workflow](#development-workflow)
2. [System Administration](#system-administration)
3. [Content Creation](#content-creation)
4. [Learning & Research](#learning--research)
5. [Custom Patterns](#custom-patterns)
6. [Automation Workflows](#automation-workflows)

---

## Development Workflow

### Example 1: Git Clone Assistant

**Scenario**: You clone a new project and need to set it up.

**Your action:**
```bash
aish
> "git clone https://github.com/awesome/project.git"
```

**What happens:**

1. **Temporal Service** records the command:
   ```json
   {
     "event_type": "command",
     "command": "git clone https://github.com/awesome/project.git",
     "exit_code": 0,
     "cwd": "/home/user/Projects"
   }
   ```

2. **Agent Service** detects the git clone pattern:
   - Extracts repo name: "project"
   - Determines project path: "/home/user/Projects/project"
   - Generates suggestion

3. **Desktop Notification** appears:
   ```
   📱 Neuralux Agent
   New Project Detected
   
   You just cloned 'project'. Would you like me to inspect 
   it for a 'requirements.txt' or 'package.json' to install 
   dependencies?
   
   [Yes, inspect]  [No, thanks]
   ```

4. **Click "Yes, inspect"** → Runs: `aish inspect /home/user/Projects/project`

5. **Agent inspects** and finds `package.json`:
   ```
   📱 Neuralux Agent
   Dependencies Found
   
   Found package.json with 15 dependencies. Install them?
   
   [npm install]  [yarn install]  [Skip]
   ```

**Timeline view:**
```bash
python tests/query_timeline.py command --limit 5
```
Output:
```
timestamp                 command                              exit_code
2025-10-31 10:23:45      git clone https://github.com/...     0
2025-10-31 10:24:12      aish inspect /home/user/Projects/... 0
2025-10-31 10:24:45      cd project && npm install            0
```

### Example 2: Docker Compose Setup

**Your action:**
```bash
> "docker-compose up -d"
```

**AI Suggestion** (via LLM, not hardcoded pattern):
```
📱 Neuralux Agent
Container Services Started

You started Docker Compose. Common next steps:
• View logs: docker-compose logs -f
• Check status: docker-compose ps
• Open web UI: http://localhost:8080

[View logs]  [Check status]  [Dismiss]
```

**If you click "View logs":**
- Opens new terminal with `docker-compose logs -f`
- Agent monitors for errors in logs
- Suggests fixes if containers fail

### Example 3: Python Virtual Environment

**Your actions:**
```bash
> "python3 -m venv venv"
> "source venv/bin/activate"
```

**AI Suggestion:**
```
📱 Neuralux Agent
Virtual Environment Active

Your venv is activated. Install requirements?

[pip install -r requirements.txt]  [Skip]
```

**After installation completes:**
```
📱 Neuralux Agent
Dependencies Installed

All dependencies installed successfully!
Run your project?

[python main.py]  [python manage.py runserver]  [Skip]
```

---

## System Administration

### Example 4: Disk Space Monitor

**What happens automatically:**

Every 5 minutes, Temporal Service takes a system snapshot:

```json
{
  "event_type": "system_snapshot",
  "cpu_percent": 45.2,
  "memory_percent": 68.5,
  "disk_usage_percent": 92.3,  ← High!
  "active_processes": 234
}
```

**Agent detects high disk usage:**
```
📱 Neuralux Agent
⚠️ Disk Space Critical

Your disk is 92% full. Let me help find large files.

[Find large files]  [Clean package cache]  [Dismiss]
```

**Click "Find large files":**
```bash
# Automatically runs
aish search --size ">1GB" ~
```

**Results shown + suggestion:**
```
📱 Neuralux Agent
Large Files Found

Found 5 files over 1GB:
• ~/Downloads/ubuntu.iso (4.2GB)
• ~/Videos/recording.mp4 (2.1GB)
• ~/.cache/pip/... (1.8GB)

[Move to external drive]  [Delete safely]  [Keep all]
```

### Example 5: Process Management

**Your action:**
```bash
> "ps aux | grep python"
```

**AI sees you're checking Python processes:**
```
📱 Neuralux Agent
Python Processes

I see 3 Python processes running. Need to manage them?

[List all Python processes]  [Kill unresponsive ones]  [Monitor resources]
```

**Click "List all Python processes":**

Uses System Service:
```python
# Behind the scenes
response = await nc.request(
    "system.action.process.list",
    json.dumps({"name": "python"}).encode()
)
```

**Shows interactive list:**
```
Python Processes:
1. PID 1234 - python manage.py runserver (2.5% CPU)
2. PID 5678 - python script.py (45.2% CPU) ← High!
3. PID 9012 - python -m jupyter notebook (1.1% CPU)

[Kill high CPU process]  [View details]  [Monitor]
```

### Example 6: Service Restart Pattern

**Your actions:**
```bash
> "sudo systemctl status nginx"
# Shows: "nginx is not running"

> "sudo systemctl start nginx"
> "sudo systemctl status nginx"
```

**AI detects restart pattern:**
```
📱 Neuralux Agent
Service Restarted

You just restarted nginx. Test if it's working?

[curl localhost]  [Check logs]  [Test config]
```

---

## Content Creation

### Example 7: Image Generation Workflow

**Your actions in overlay:**
```
> "generate an image of a serene mountain landscape"
[Image generates]

> "save it to my Pictures folder"
```

**Behind the scenes:**

1. **Temporal records** both commands
2. **Agent recognizes** image → save workflow
3. **Suggests** similar workflows:

```
📱 Neuralux Agent
Image Workflow Detected

You generated and saved an image. Create more?

[Generate similar]  [Create variations]  [Start new series]
```

### Example 8: Document Creation

**Your actions:**
```bash
> "create document outline.md"
> "write project proposal in outline.md"
```

**AI Suggestion:**
```
📱 Neuralux Agent
Document Created

You created outline.md. Common next steps:

• Preview: markdown outline.md
• Convert to PDF: pandoc outline.md -o outline.pdf
• Share: upload to Drive

[Preview]  [Convert to PDF]  [Share]
```

---

## Learning & Research

### Example 9: Tutorial Following

**Your actions:**
```bash
> "search the web for docker tutorial"
[Opens browser with results]

> "docker pull nginx"
> "docker run -p 8080:80 nginx"
```

**AI recognizes learning pattern:**
```
📱 Neuralux Agent
Learning Docker?

I see you're following a Docker tutorial. Would you like:

• Bookmark useful commands
• Create a practice project
• Get interactive Docker guide

[Create practice project]  [Interactive guide]  [Continue alone]
```

**Click "Create practice project":**
```bash
# Automatically creates:
mkdir ~/Projects/docker-practice
cd ~/Projects/docker-practice
cat > Dockerfile << EOF
FROM nginx:alpine
COPY . /usr/share/nginx/html
EOF

echo "Edit Dockerfile and run: docker build -t my-app ."
```

### Example 10: Command Learning

**Your action:**
```bash
> "how do I find large files?"
[AI explains find command]

> "find . -type f -size +100M"
[Shows results]
```

**AI offers to save:**
```
📱 Neuralux Agent
Useful Command?

You just used a complex find command. Save it for later?

[Save to favorites]  [Create alias]  [Share]
```

**Click "Create alias":**
```bash
# Adds to ~/.bashrc
alias findlarge='find . -type f -size +100M -exec ls -lh {} \;'

# Notifies you
echo "Added alias 'findlarge' to your shell"
source ~/.bashrc
```

---

## Custom Patterns

### Example 11: Creating a Build Pattern

**Goal**: Detect when you run build commands and offer deployment.

**Create pattern:**

```python
# In services/agent/patterns.py

class BuildPattern:
    """Detects project build commands."""
    
    def process_event(self, event_data):
        if event_data.get("event_type") != "command":
            return None
        
        command = event_data.get("command", "")
        build_commands = [
            "npm run build",
            "yarn build",
            "make build",
            "cargo build --release",
            "mvn package"
        ]
        
        if any(cmd in command for cmd in build_commands):
            return {
                "id": "build_completed",
                "title": "Build Completed",
                "message": "Your project built successfully. Deploy it?",
                "actions": [
                    {"label": "Deploy to staging", "command": "npm run deploy:staging"},
                    {"label": "Deploy to production", "command": "npm run deploy:prod"},
                    {"label": "Test locally", "command": "npm run serve"}
                ]
            }
        
        return None
```

**Register it:**
```python
# In PatternMatcher.__init__
self.patterns = [
    GitClonePattern(),
    BuildPattern(),  # Add here
]
```

**Test it:**
```bash
# Restart agent service
pkill -f "services/agent/service.py"
python services/agent/service.py &

# Run a build
aish
> "npm run build"
```

**You'll get:**
```
📱 Neuralux Agent
Build Completed

Your project built successfully. Deploy it?

[Deploy to staging]  [Deploy to production]  [Test locally]
```

### Example 12: Database Migration Pattern

**Pattern code:**
```python
class MigrationPattern:
    """Detects database migrations."""
    
    def process_event(self, event_data):
        command = event_data.get("command", "")
        
        migration_commands = [
            "python manage.py migrate",
            "rails db:migrate",
            "alembic upgrade head",
            "flyway migrate"
        ]
        
        if any(cmd in command for cmd in migration_commands):
            return {
                "id": "migration_completed",
                "title": "Database Migration",
                "message": "Database migrated. Create backup?",
                "actions": [
                    {"label": "Backup database", "command": "pg_dump mydb > backup.sql"},
                    {"label": "Check status", "command": "python manage.py showmigrations"},
                    {"label": "Skip", "command": "ignore"}
                ]
            }
        
        return None
```

---

## Automation Workflows

### Example 13: Morning Routine Automation

**Goal**: Detect when you start working and prepare your environment.

**Pattern:**
```python
class MorningRoutinePattern:
    """Detects morning work session start."""
    
    def __init__(self):
        self.last_activity = None
    
    def process_event(self, event_data):
        import datetime
        now = datetime.datetime.now()
        
        # First activity between 7am-10am after 12 hours idle
        if event_data.get("event_type") != "command":
            return None
        
        if self.last_activity and (now - self.last_activity).seconds > 43200:
            if 7 <= now.hour <= 10:
                self.last_activity = now
                return {
                    "id": "morning_routine",
                    "title": "Good Morning!",
                    "message": "Start your daily setup?",
                    "actions": [
                        {"label": "Open projects", "command": "aish open ~/Projects"},
                        {"label": "Check updates", "command": "aish health"},
                        {"label": "Skip", "command": "ignore"}
                    ]
                }
        
        self.last_activity = now
        return None
```

### Example 14: End of Day Cleanup

**Pattern:**
```python
class EndOfDayPattern:
    """Suggests cleanup at end of workday."""
    
    def process_event(self, event_data):
        import datetime
        now = datetime.datetime.now()
        
        # Between 5pm-7pm, if working directory has uncommitted changes
        if 17 <= now.hour <= 19:
            cwd = event_data.get("cwd", "")
            if self._has_uncommitted_changes(cwd):
                return {
                    "id": "end_of_day_cleanup",
                    "title": "Uncommitted Changes",
                    "message": "You have uncommitted changes. Commit before ending day?",
                    "actions": [
                        {"label": "Review changes", "command": "git status"},
                        {"label": "Commit all", "command": "git add -A && git commit"},
                        {"label": "Remind me later", "command": "ignore"}
                    ]
                }
        
        return None
    
    def _has_uncommitted_changes(self, cwd):
        import subprocess
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except:
            return False
```

### Example 15: Context Switching Helper

**Goal**: When switching projects, set up the new context automatically.

**Implementation:**
```python
class ProjectSwitchPattern:
    """Detects project directory changes."""
    
    def __init__(self):
        self.last_project = None
    
    def process_event(self, event_data):
        if event_data.get("event_type") != "command":
            return None
        
        command = event_data.get("command", "")
        cwd = event_data.get("cwd", "")
        
        # Detect 'cd' to a project directory
        if command.startswith("cd ") and "/Projects/" in cwd:
            project_name = cwd.split("/Projects/")[1].split("/")[0]
            
            if project_name != self.last_project:
                self.last_project = project_name
                return {
                    "id": "project_switched",
                    "title": f"Switched to {project_name}",
                    "message": "Set up your workspace?",
                    "actions": [
                        {"label": "Open in VS Code", "command": f"code {cwd}"},
                        {"label": "Start dev server", "command": "npm run dev"},
                        {"label": "Pull latest", "command": "git pull"},
                        {"label": "Just browse", "command": "ignore"}
                    ]
                }
        
        return None
```

**Usage:**
```bash
> "cd ~/Projects/my-app"
```

**Notification:**
```
📱 Neuralux Agent
Switched to my-app

Set up your workspace?

[Open in VS Code]  [Start dev server]  [Pull latest]  [Just browse]
```

---

## Advanced: Multi-Step Workflows

### Example 16: Full Stack Development Flow

**Scenario**: Complete workflow from idea to deployment.

**Your actions:**
```bash
# 1. Create project
> "create new react app called my-dashboard"

# 2. Add features
> "add chart library to package.json"

# 3. Develop
> "start development server"

# 4. Test
> "run tests"

# 5. Build
> "build for production"

# 6. Deploy
> "deploy to vercel"
```

**Agent tracks entire workflow:**

At each step, it offers contextual suggestions:

```
Step 1: Project created
└─> [Install dependencies]  [Open in editor]

Step 2: Dependency added
└─> [Install new package]  [Check documentation]

Step 3: Dev server starting
└─> [Open in browser]  [View logs]

Step 4: Tests running
└─> [Fix failing tests]  [View coverage]

Step 5: Build complete
└─> [Test production build]  [Deploy]

Step 6: Deployment initiated
└─> [View deployment]  [Test live site]
```

**View complete workflow:**
```bash
python tests/query_timeline.py command --limit 10
```

### Example 17: Data Analysis Workflow

**Your actions:**
```bash
> "download dataset from https://example.com/data.csv"
> "explore data.csv"
> "create visualization from data.csv"
> "generate report with insights"
```

**Agent suggestions at each step:**

```
Downloaded dataset (2.5MB)
└─> [Preview data]  [Check for missing values]

Data explored
└─> [Clean data]  [Remove outliers]  [Export summary]

Visualization created
└─> [Save as PNG]  [Generate interactive plot]  [Create dashboard]

Report generated
└─> [Export to PDF]  [Share via email]  [Upload to Drive]
```

---

## Viewing Your Workflows

### Query Specific Workflows

```bash
# Last 20 commands
python tests/query_timeline.py command --limit 20

# Recent file changes
python tests/query_timeline.py file --limit 20

# System snapshots (monitoring)
python tests/query_timeline.py system_snapshot --limit 10

# Everything
python tests/query_timeline.py all --limit 50
```

### Analyze Patterns

```python
#!/usr/bin/env python3
# analyze_workflows.py

import duckdb
from collections import Counter

DB_PATH = "data/temporal/timeline.duckdb"

# Connect to timeline
con = duckdb.connect(DB_PATH, read_only=True)

# Find most common commands
result = con.execute("""
    SELECT 
        command, 
        COUNT(*) as count
    FROM command_events
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY command
    ORDER BY count DESC
    LIMIT 10
""").fetchall()

print("Top 10 commands (last 7 days):")
for cmd, count in result:
    print(f"  {count:3d}x  {cmd[:60]}")

# Find busiest hours
result = con.execute("""
    SELECT 
        HOUR(timestamp) as hour,
        COUNT(*) as count
    FROM command_events
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY hour
    ORDER BY hour
""").fetchall()

print("\nActivity by hour:")
for hour, count in result:
    bar = "█" * (count // 2)
    print(f"  {hour:02d}:00  {bar} ({count})")

con.close()
```

**Output:**
```
Top 10 commands (last 7 days):
   45x  git status
   32x  ls -la
   28x  npm run dev
   24x  docker-compose up -d
   19x  python manage.py runserver

Activity by hour:
  09:00  ████████████ (24)
  10:00  ████████████████ (32)
  11:00  ██████████ (20)
  14:00  ████████████████████ (40)
  15:00  ████████████████ (32)
```

---

## Summary

Phase 3's proactive intelligence works by:

1. **📝 Recording** everything you do (commands, files, system state)
2. **🧠 Analyzing** patterns and context
3. **💡 Suggesting** helpful next steps
4. **⚡ Acting** when you approve

**Key Benefits:**
- ✅ Learn from your workflows
- ✅ Reduce repetitive tasks
- ✅ Never forget follow-up steps
- ✅ Customize with your own patterns

**Get Started:**
```bash
# Ensure services are running
aish status

# Try it with a git clone
aish
> "git clone https://github.com/your/favorite-repo.git"

# Watch for the notification! 🔔
```

**Next Steps:**
- Read [User Guide](PHASE_3_USER_GUIDE.md) for complete documentation
- Read [Architecture](PHASE_3_ARCHITECTURE.md) for technical details
- Create your own patterns for your workflows
- Share patterns with the community!

---

**Have ideas for new patterns? Let us know!** 🚀

*Built with ❤️ by the Neuralux community*

