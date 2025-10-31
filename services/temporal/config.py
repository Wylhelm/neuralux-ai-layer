import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Assumes the service is run from its directory `services/temporal`
PROJECT_ROOT = Path(__file__).parent.parent.parent

# --- General Service Settings ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SERVICE_NAME = "temporal_service"

# --- NATS Connection ---
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

# --- Storage Settings ---
STORAGE_PATH = os.getenv("TEMPORAL_STORAGE_PATH", str(PROJECT_ROOT / "data" / "temporal"))
DB_FILENAME = "timeline.duckdb"

# --- Collector Settings ---
# How often to take a snapshot of active windows, processes, etc. (in seconds)
SNAPSHOT_INTERVAL = int(os.getenv("TEMPORAL_SNAPSHOT_INTERVAL", 300)) # 5 minutes

# Directories to watch for filesystem events
WATCHED_DIRECTORIES = os.getenv("TEMPORAL_WATCHED_DIRECTORIES", "~/Documents,~/Projects").split(',')
