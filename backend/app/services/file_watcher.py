from __future__ import annotations

import logging
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..config import Settings
from .profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    def __init__(self, manager: ProfileManager):
        self._manager = manager

    def _handle(self, event) -> None:
        if getattr(event, "is_directory", False):
            return
        dest = getattr(event, "dest_path", None)
        path = Path(dest if dest else event.src_path)
        if not path.name.endswith((".json", ".json.gz")):
            return
        logger.debug("Watcher event %s: %s", event.__class__.__name__, path)
        # Debounce: the manager's scan loop picks this up on its next tick.
        self._manager.request_scan()

    def on_created(self, event):
        self._handle(event)

    def on_modified(self, event):
        self._handle(event)

    def on_moved(self, event):
        self._handle(event)


class FileWatcher:
    """Watchdog-based filesystem watcher for the profile root."""

    def __init__(self, settings: Settings, manager: ProfileManager):
        self._settings = settings
        self._manager = manager
        self._observer: Observer | None = None

    def start(self) -> None:
        root = self._settings.profile_root
        if not root.exists():
            logger.warning(
                "Profile root %s does not exist; watcher idle until it appears",
                root,
            )
            return
        self._observer = Observer()
        self._observer.schedule(
            _Handler(self._manager), str(root), recursive=True
        )
        self._observer.start()
        logger.info("File watcher started on %s", root)

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("File watcher stopped")
