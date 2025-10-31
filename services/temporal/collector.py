import asyncio
import logging
import psutil
import getpass
from Xlib import display, X
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from typing import Callable, Coroutine

from services.temporal import config
from services.temporal.models import AppFocusEvent, FileEvent, SystemSnapshotEvent, CommandEvent

logger = logging.getLogger(config.SERVICE_NAME)

# Type alias for the async callback
EventCallback = Callable[[AppFocusEvent | FileEvent | SystemSnapshotEvent], Coroutine]

def get_active_window_info():
    """Gets the active window's title and application name on X11."""
    try:
        d = display.Display()
        root = d.screen().root
        window_id = root.get_full_property(d.intern_atom('_NET_ACTIVE_WINDOW'), X.AnyPropertyType).value[0]
        window = d.create_resource_object('window', window_id)
        
        title = window.get_full_property(d.intern_atom('_NET_WM_NAME'), 0).value.decode('utf-8', 'ignore')
        
        wm_class = window.get_wm_class()
        app_name = wm_class[1] if wm_class else "Unknown"
        
        return app_name, title
    except Exception as e:
        logger.warning(f"Could not get active window info: {e}")
        return "Unknown", "Unknown"

class SystemSnapshotCollector:
    """Periodically collects snapshots of the system state."""

    def __init__(self, callback: EventCallback):
        self.callback = callback
        self.interval = config.SNAPSHOT_INTERVAL
        self._task = None

    async def start(self):
        logger.info(f"Starting system snapshot collector with {self.interval}s interval.")
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        if self._task:
            self._task.cancel()
            logger.info("System snapshot collector stopped.")

    async def _run(self):
        while True:
            try:
                await self.take_snapshot()
            except Exception as e:
                logger.error(f"Error taking system snapshot: {e}")
            await asyncio.sleep(self.interval)

    async def take_snapshot(self):
        app_name, window_title = get_active_window_info()
        processes = [p.name() for p in psutil.process_iter(['name'])]
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        snapshot = SystemSnapshotEvent(
            active_app_name=app_name,
            active_window_title=window_title,
            running_processes=processes,
            cpu_usage=cpu,
            memory_usage=mem,
        )
        await self.callback(snapshot)
        logger.debug("System snapshot taken.")

class FilesystemCollector(FileSystemEventHandler):
    """Monitors filesystem events in specified directories."""

    def __init__(self, callback: EventCallback):
        self.callback = callback
        self.observer = Observer()
        self.user = getpass.getuser()

    def start(self):
        watched_dirs = [str(Path(p).expanduser()) for p in config.WATCHED_DIRECTORIES]
        logger.info(f"Starting filesystem collector for directories: {watched_dirs}")
        for path in watched_dirs:
            if Path(path).exists():
                self.observer.schedule(self, path, recursive=True)
            else:
                logger.warning(f"Directory not found, cannot watch: {path}")
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("Filesystem collector stopped.")

    def on_any_event(self, event):
        """Catches all events and dispatches them to the handler."""
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(asyncio.create_task, self.handle_event(event))

    async def handle_event(self, event):
        """Asynchronously handles a single filesystem event."""
        change_type_map = {
            'created': 'created',
            'deleted': 'deleted',
            'modified': 'modified',
            'moved': 'moved'
        }
        
        event_type = event.event_type
        if event_type not in change_type_map:
            return

        file_event = FileEvent(
            path=event.src_path,
            change_type=change_type_map[event_type],
            is_directory=event.is_directory,
            user=self.user
        )
        await self.callback(file_event)
        logger.debug(f"Filesystem event: {file_event.model_dump_json()}")

class CommandCollector:
    """Listens for shell command events published on the message bus."""

    def __init__(self, callback: EventCallback, subject: str = "temporal.command.new"):
        self.callback = callback
        self.subject = subject
        self._subscription = None
        self._nc = None

    async def start(self, nc) -> None:
        """Start listening for command events using the provided NATS client."""
        self._nc = nc

        async def _handler(msg):
            try:
                data = msg.data.decode()
                event = CommandEvent.parse_raw(data)
            except Exception as exc:
                logger.error("Failed to parse command event: %s", exc)
                return

            try:
                await self.callback(event)
            except Exception as exc:
                logger.error("Command event callback failed: %s", exc)

        self._subscription = await nc.subscribe(self.subject, cb=_handler)
        logger.info("Command collector subscribed to %s", self.subject)

    async def stop(self) -> None:
        """Stop listening for command events."""
        if self._subscription is not None:
            try:
                await self._subscription.unsubscribe()
            except Exception as exc:
                logger.warning("Failed to unsubscribe command collector: %s", exc)
            finally:
                self._subscription = None

        self._nc = None
