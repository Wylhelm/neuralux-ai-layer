import json
import logging
import os
import shlex
from typing import Dict, Any, Optional

from services.agent import config

logger = logging.getLogger(config.SERVICE_NAME)

class GitClonePattern:
    """Detects when a user clones a Git repository."""

    def __init__(self):
        self.recent_commands = []

    def process_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processes a command event and returns a suggestion if the pattern is matched.
        """
        logger.debug(f"GitClonePattern processing event: {event_data.get('event_type')}")

        if event_data.get("event_type") != "command":
            return None

        command_text = event_data.get("command") or ""
        if not command_text:
            return None

        try:
            tokens = shlex.split(command_text)
        except ValueError:
            return None

        if len(tokens) < 2:
            return None

        if tokens[0].lower() != "git" or tokens[1].lower() != "clone":
            return None

        exit_code = event_data.get("exit_code")
        if exit_code not in (None, 0):
            # Ignore failed clone attempts
            return None

        options_with_value = {
            "-b",
            "--branch",
            "--depth",
            "--shallow-since",
            "--shallow-exclude",
            "--origin",
            "--reference",
            "--dissociate",
            "--separate-git-dir",
            "--upload-pack",
            "--template",
            "--server-option",
            "--config",
            "--filter",
            "--jobs",
        }

        token_iter = iter(tokens[2:])
        repo_url = None
        dest_path = None

        for token in token_iter:
            if token.startswith("-"):
                if "=" not in token and token in options_with_value:
                    next(token_iter, None)
                continue
            repo_url = token
            break

        if repo_url is None:
            return None

        for token in token_iter:
            if token.startswith("-"):
                if "=" not in token and token in options_with_value:
                    next(token_iter, None)
                continue
            dest_path = token
            break

        repo_name = dest_path or repo_url.rstrip("/").split("/")[-1]
        repo_name = repo_name.replace(".git", "").strip() or "new project"

        cwd = event_data.get("cwd") or ""
        project_path = dest_path or repo_name
        if cwd and not os.path.isabs(project_path):
            project_path = os.path.join(cwd, project_path)

        project_path = os.path.normpath(project_path)
        inspect_command = f"aish inspect {shlex.quote(project_path)}"

        suggestion = {
            "id": "git_clone_detected",
            "title": "New Project Detected",
            "message": (
                f"You just cloned '{repo_name}'. Would you like me to inspect it for a "
                "'requirements.txt' or 'package.json' to install dependencies?"
            ),
            "actions": [
                {"label": "Yes, inspect", "command": inspect_command},
                {"label": "No, thanks", "command": "ignore"},
            ],
        }
        return suggestion

class PatternMatcher:
    """Manages and applies all registered patterns."""

    def __init__(self, suggestion_engine=None):
        self.patterns = [GitClonePattern()]
        self.suggestion_engine = suggestion_engine

    async def match(self, event_subject: str, event_data_str: str) -> Optional[Dict[str, Any]]:
        """
        Parses an event and checks it against all patterns.
        Returns the first matched suggestion.
        """
        try:
            event_data = json.loads(event_data_str)
        except json.JSONDecodeError:
            logger.warning("Could not decode event data.")
            return None

        for pattern in self.patterns:
            suggestion = pattern.process_event(event_data)
            if suggestion:
                return suggestion

        if self.suggestion_engine:
            return await self.suggestion_engine.suggest_for_event(event_data)

        return None
