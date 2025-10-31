import os
from dotenv import load_dotenv

load_dotenv()

# --- General Service Settings ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SERVICE_NAME = "system_service"

# --- NATS Connection ---
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

# --- System Service Settings ---
# The NATS subject prefix for system actions
ACTION_SUBJECT_PREFIX = "system.action"
