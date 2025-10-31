import logging
import json
import asyncio
import shutil
import subprocess
from typing import Dict, Any

from services.agent import config

logger = logging.getLogger(config.SERVICE_NAME)

async def send_notification(suggestion: Dict[str, Any], nats_client):
    """
    Publishes a suggestion to the NATS message bus and mirrors it to the desktop.
    """
    subject = "agent.suggestion"
    payload = json.dumps(suggestion).encode()
    
    try:
        await nats_client.publish(subject, payload)
        logger.info(f"Published suggestion to {subject}: {suggestion}")
    except Exception as e:
        logger.error(f"Failed to publish suggestion: {e}")

    # Best-effort desktop notification (no need for separate `aish agent` process)
    if shutil.which("notify-send"):
        title = suggestion.get("title") or "Neuralux Agent"
        message = suggestion.get("message") or "New suggestion available."
        actions = suggestion.get("actions") or []
        if isinstance(actions, list) and actions:
            hints = [f"• {a.get('label')}: {a.get('command')}" for a in actions if a.get("label")]
            if hints:
                message = f"{message}\n\n" + "\n".join(hints[:3])

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [
                        "notify-send",
                        "--app-name=NeuraluxAgent",
                        "--icon=utilities-terminal",
                        "--",
                        title,
                        message,
                    ],
                    check=False,
                ),
            )
        except Exception as exc:
            logger.debug("Desktop notification failed", exc_info=exc)
