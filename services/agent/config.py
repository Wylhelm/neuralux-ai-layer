import os
from dotenv import load_dotenv

load_dotenv()

# --- General Service Settings ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SERVICE_NAME = "agent_service"

# --- NATS Connection ---
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

# --- Agent Settings ---
# The NATS subject to listen to for temporal events
EVENT_STREAM_SUBJECT = "temporal.event.>"
