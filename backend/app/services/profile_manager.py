from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Optional

from ..config import Settings
from ..models.profile import ProfileRecord, ProfileStatus
from ..models.trace import ParsedTrace
from .semantic_mapper import SemanticMapper
from .source_mapper import SourceMapper
from .step_detector import attribute_events_to_steps, detect_steps
from .trace_parser import (
    TraceParseError,
    build_trace,
    detect_pids,
    normalize_events,
    read_trace_file,
)

logger = logging.getLogger(__name__)

CANDIDATE_SUFFIXES = (".json", ".json.gz")


def _is_candidate(path: Path) -> bool:
    return path.name.endswith(CANDIDATE_SUFFIXES)


class ProfileManager:
    """Registry + lifecycle manager for discovered profile files.

    Responsibilities:
      - recursive scan of the profile root
      - file-stability check before parsing (partial-file protection)
      - parse / normalize / step-detect / classify / aggregate
      - LRU cache of parsed traces
      - emit lifecycle events to an async sink (WebSocket broadcast)
    """

    def __init__(
        self,
        settings: Settings,
        mapper: SemanticMapper,
        source_mapper: SourceMapper,
    ):
        self.settings = settings
        self.mapper = mapper
        self.source_mapper = source_mapper
        self._profiles: dict[str, ProfileRecord] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="profile-parse"
        )
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._sink: Optional[Callable[[dict], Any]] = None
        self._scan_trigger: Optional[asyncio.Event] = None
        self._last_scan: Optional[float] = None
        self._monitoring = False

    # ------------------------------------------------------------------ wiring

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def set_event_sink(self, sink: Callable[[dict], Any]) -> None:
        self._sink = sink

    def set_scan_trigger(self, event: asyncio.Event) -> None:
        self._scan_trigger = event

    def request_scan(self) -> None:
        """Thread-safe request for an out-of-band scan (from the watcher)."""
        if self._loop is not None and self._scan_trigger is not None:
            self._loop.call_soon_threadsafe(self._scan_trigger.set)

    def shutdown(self) -> None:
        self._monitoring = False
        self._executor.shutdown(wait=False)

    # ------------------------------------------------------------------ helpers

    def _emit(self, message: dict[str, Any]) -> None:
        if self._sink is None or self._loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._sink(message), self._loop)
        except RuntimeError:
            pass

    @staticmethod
    def _profile_id(path: Path) -> str:
        return hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _is_stable(path: Path, delay: float) -> bool:
        try:
            st1 = path.stat()
        except OSError:
            return False
        if st1.st_size == 0:
            return False
        if delay > 0:
            time.sleep(delay)
        try:
            st2 = path.stat()
        except OSError:
            return False
        return st1.st_size == st2.st_size

    # ------------------------------------------------------------------ scanning

    def scan(self) -> None:
        """Scan the profile root, register new files, and start parsing stable ones.

        Runs in a worker thread (never on the event loop).
        """
        root = self.settings.profile_root
        with self._lock:
            self._monitoring = root.exists()
            if not self._monitoring:
                logger.warning("Profile root %s does not exist", root)
                self._last_scan = time.time()
                self._emit(self._monitor_status())
                return

            found: dict[str, Path] = {}
            for path in root.rglob("*"):
                try:
                    if path.is_file() and _is_candidate(path):
                        found[self._profile_id(path)] = path
                except OSError:
                    continue

            now = time.time()

            # Register new files.
            for pid, path in found.items():
                if pid not in self._profiles:
                    try:
                        st = path.stat()
                    except OSError:
                        continue
                    rec = ProfileRecord(
                        id=pid,
                        path=str(path),
                        size_bytes=st.st_size,
                        mtime=st.st_mtime,
                        status=ProfileStatus.DISCOVERED,
                        discovered_at=now,
                    )
                    self._profiles[pid] = rec
                    logger.info("Profile discovered: %s", path)
                    self._emit(
                        {
                            "type": "profile_discovered",
                            "profileId": pid,
                            "profile": rec.to_summary(),
                        }
                    )

            # Detect removed files.
            for pid in list(self._profiles.keys()):
                if pid not in found:
                    rec = self._profiles[pid]
                    if rec.status not in (ProfileStatus.REMOVED,):
                        rec.status = ProfileStatus.REMOVED
                        rec.trace = None
                        logger.info("Profile removed: %s", rec.path)
                        self._emit({"type": "profile_removed", "profileId": pid})

            # Detect changed files (size/mtime) and invalidate their cache.
            for pid, path in found.items():
                rec = self._profiles[pid]
                try:
                    st = path.stat()
                except OSError:
                    continue
                changed = (
                    rec.size_bytes != st.st_size
                    or abs(rec.mtime - st.st_mtime) > 0.001
                )
                if changed and rec.status in (
                    ProfileStatus.READY,
                    ProfileStatus.FAILED_TEMPORARY,
                    ProfileStatus.DISCOVERED,
                ):
                    logger.info("Profile changed, invalidating: %s", path)
                    rec.trace = None
                    rec.size_bytes = st.st_size
                    rec.mtime = st.st_mtime
                    rec.status = ProfileStatus.DISCOVERED
                    rec.error = None

            # Start parsing for discovered / retryable files that are stable.
            for rec in list(self._profiles.values()):
                if rec.status in (
                    ProfileStatus.DISCOVERED,
                    ProfileStatus.FAILED_TEMPORARY,
                ):
                    path = Path(rec.path)
                    if not path.exists():
                        continue
                    if self._is_stable(path, self.settings.file_stability_delay):
                        self._start_parse(rec)

            self._last_scan = time.time()

        self._emit(self._monitor_status())

    def _start_parse(self, rec: ProfileRecord) -> None:
        rec.status = ProfileStatus.PARSING
        rec.error = None
        self._emit({"type": "profile_parsing", "profileId": rec.id})
        self._executor.submit(self._parse_profile, rec)

    # ------------------------------------------------------------------ parsing

    def _parse_profile(self, rec: ProfileRecord) -> None:
        try:
            trace = self._do_parse(rec)
            with self._lock:
                rec.trace = trace
                rec.status = ProfileStatus.READY
                rec.error = None
                rec.parsed_at = time.time()
                rec.event_count = len(trace.events)
                rec.step_count = len(trace.steps)
                rec.trace_start_us = trace.trace_start_us
                rec.trace_end_us = trace.trace_end_us
                self._enforce_lru()
            logger.info(
                "Profile ready: %s (%d events, %d steps)",
                rec.path,
                rec.event_count,
                rec.step_count,
            )
            self._emit(
                {
                    "type": "profile_ready",
                    "profileId": rec.id,
                    "profile": rec.to_summary(),
                }
            )
        except TraceParseError as exc:
            with self._lock:
                rec.status = (
                    ProfileStatus.FAILED_TEMPORARY
                    if exc.temporary
                    else ProfileStatus.FAILED
                )
                rec.error = str(exc)
            logger.error("Profile parse failed (%s): %s", rec.path, exc)
            self._emit(
                {
                    "type": "profile_failed",
                    "profileId": rec.id,
                    "error": str(exc),
                    "temporary": exc.temporary,
                }
            )
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                rec.status = ProfileStatus.FAILED
                rec.error = f"Unexpected error: {exc}"
            logger.exception("Profile parse crashed: %s", rec.path)
            self._emit(
                {
                    "type": "profile_failed",
                    "profileId": rec.id,
                    "error": rec.error,
                    "temporary": False,
                }
            )

    def _do_parse(self, rec: ProfileRecord) -> ParsedTrace:
        path = Path(rec.path)
        data = read_trace_file(path)
        events, meta = normalize_events(data)
        cpu_pid, gpu_pids = detect_pids(events)
        steps = detect_steps(events, cpu_pid)
        attribute_events_to_steps(events, steps, cpu_pid)
        for ev in events:
            rule = self.mapper.classify(ev.raw_name)
            if rule is not None:
                ev.semantic_category = rule.category
                ev.semantic_name = rule.display_name
                ev.confidence = rule.confidence
                ev.framework = rule.framework
                ev.rule_id = rule.id
            else:
                ev.semantic_category = "UNKNOWN"
                ev.semantic_name = None
                ev.confidence = "unknown"
        trace = build_trace(events, meta, steps, cpu_pid, gpu_pids)
        logger.info(
            "Semantic mapping completed for %s (%d rules loaded)",
            path.name,
            len(self.mapper.rules),
        )
        return trace

    def _enforce_lru(self) -> None:
        """Unload the oldest parsed traces beyond max_loaded_profiles.

        Must be called with self._lock held. Unloaded profiles keep their
        metadata and can be re-parsed on demand via ensure_loaded().
        """
        loaded = [
            r
            for r in self._profiles.values()
            if r.trace is not None and r.status == ProfileStatus.READY
        ]
        if len(loaded) <= self.settings.max_loaded_profiles:
            return
        loaded.sort(key=lambda r: r.parsed_at or 0.0)
        for r in loaded[: len(loaded) - self.settings.max_loaded_profiles]:
            r.trace = None
            logger.info("Unloaded profile from cache (LRU): %s", r.path)

    # ------------------------------------------------------------------ access

    def list_profiles(self) -> list[ProfileRecord]:
        with self._lock:
            return sorted(
                self._profiles.values(), key=lambda r: (r.mtime, r.path)
            )

    def get(self, profile_id: str) -> Optional[ProfileRecord]:
        with self._lock:
            return self._profiles.get(profile_id)

    def ensure_loaded(self, rec: ProfileRecord) -> ParsedTrace:
        """Return the parsed trace, re-parsing synchronously if unloaded."""
        if rec.trace is not None:
            return rec.trace
        if rec.status != ProfileStatus.READY:
            raise ProfileNotFoundError(
                f"Profile {rec.id} is not ready (status={rec.status.value})"
            )
        self._parse_profile(rec)
        if rec.trace is None:
            raise ProfileNotFoundError(f"Profile {rec.id} failed to load")
        return rec.trace

    def monitor_status(self) -> dict[str, Any]:
        with self._lock:
            profiles = list(self._profiles.values())
            return {
                "monitoring": self._monitoring,
                "profileRoot": str(self.settings.profile_root),
                "lastScan": self._last_scan,
                "profileCount": len(profiles),
                "readyCount": sum(
                    1 for p in profiles if p.status == ProfileStatus.READY
                ),
            }

    def _monitor_status(self) -> dict[str, Any]:
        return {"type": "monitor_status", "monitor": self.monitor_status()}


class ProfileNotFoundError(Exception):
    pass
