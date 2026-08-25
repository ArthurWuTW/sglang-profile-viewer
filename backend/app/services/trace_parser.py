from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path
from typing import Any, Optional

from ..models.event import TraceEvent
from ..models.step import ExecutionStep
from ..models.trace import ParsedTrace

logger = logging.getLogger(__name__)


class TraceParseError(Exception):
    """Raised when a profile file cannot be parsed.

    ``temporary`` indicates the failure is likely transient (e.g. the file is
    still being written) and the file should be retried later.
    """

    def __init__(self, message: str, temporary: bool = False):
        super().__init__(message)
        self.temporary = temporary


def read_trace_file(path: Path) -> dict[str, Any]:
    """Read and decode a (possibly gzipped) Chrome-trace JSON file."""
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
                text = f.read()
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
        raise TraceParseError(
            f"Failed to read/decompress {path.name}: {exc}", temporary=True
        ) from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TraceParseError(
            f"Invalid JSON in {path.name}: {exc}", temporary=True
        ) from exc
    if not isinstance(data, dict) or "traceEvents" not in data:
        raise TraceParseError(
            f"Unsupported trace format in {path.name}: missing 'traceEvents'",
            temporary=False,
        )
    if not isinstance(data["traceEvents"], list):
        raise TraceParseError(
            f"Unsupported trace format in {path.name}: 'traceEvents' is not a list",
            temporary=False,
        )
    return data


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def normalize_events(data: dict[str, Any]) -> tuple[list[TraceEvent], dict[str, Any]]:
    """Convert raw ``traceEvents`` into normalized :class:`TraceEvent` objects.

    The raw ``args`` dict is preserved by reference so the original event can be
    reconstructed losslessly (see :meth:`TraceEvent.to_raw`).
    """
    raw_events = data["traceEvents"]
    events: list[TraceEvent] = []
    for idx, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        if not isinstance(name, str):
            continue
        ts = _as_float(raw.get("ts"))
        if ts is None:
            ts = 0.0
        dur = _as_float(raw.get("dur"))
        args = raw.get("args")
        if not isinstance(args, dict):
            args = {}
        phase = raw.get("ph")
        phase = phase if isinstance(phase, str) else None
        cat = raw.get("cat")
        cat = cat if isinstance(cat, str) else None
        flow_id = _as_int(raw.get("id")) if phase in ("f", "s", "e") else None
        events.append(
            TraceEvent(
                id=idx,
                raw_name=name,
                category=cat,
                phase=phase,
                timestamp_us=ts,
                duration_us=dur,
                process_id=_as_int(raw.get("pid")),
                thread_id=_as_int(raw.get("tid")),
                args=args,
                flow_id=flow_id,
            )
        )
    device_properties = data.get("deviceProperties")
    meta = {
        "device_properties": device_properties
        if isinstance(device_properties, list)
        else [],
        "trace_name": data.get("traceName")
        if isinstance(data.get("traceName"), str)
        else None,
    }
    return events, meta


def detect_pids(events: list[TraceEvent]) -> tuple[Optional[int], list[int]]:
    """Identify the CPU (scheduler) pid and the GPU pids.

    Uses ``process_labels`` metadata events when present; falls back to the pid
    with the most events for the CPU pid.
    """
    labels: dict[int, str] = {}
    for ev in events:
        if ev.phase == "M" and ev.raw_name == "process_labels":
            lbl = ev.args.get("labels")
            if isinstance(lbl, str) and ev.process_id is not None:
                labels[ev.process_id] = lbl
    cpu_pid: Optional[int] = None
    gpu_pids: list[int] = []
    for pid, lbl in labels.items():
        up = lbl.strip().upper()
        if up == "CPU":
            cpu_pid = pid
        elif up.startswith("GPU"):
            gpu_pids.append(pid)
    if cpu_pid is None:
        counts: dict[int, int] = {}
        for ev in events:
            if ev.process_id is not None:
                counts[ev.process_id] = counts.get(ev.process_id, 0) + 1
        if counts:
            cpu_pid = max(counts, key=lambda p: (counts[p], -p))
    return cpu_pid, gpu_pids


def build_trace(
    events: list[TraceEvent],
    meta: dict[str, Any],
    steps: list[ExecutionStep],
    cpu_pid: Optional[int],
    gpu_pids: list[int],
) -> ParsedTrace:
    """Assemble a :class:`ParsedTrace` with its derived indexes."""
    timed = [ev for ev in events if ev.duration_us is not None]
    if timed:
        start = min(ev.timestamp_us for ev in timed)
        end = max(ev.end_us for ev in timed)
    else:
        start = end = 0.0

    correlation_to_runtime: dict[int, int] = {}
    for ev in events:
        if ev.category == "cuda_runtime" and ev.phase == "X":
            corr = ev.args.get("correlation")
            if isinstance(corr, int):
                correlation_to_runtime[corr] = ev.id

    flow_index: dict[int, list[int]] = {}
    for ev in events:
        if ev.flow_id is not None:
            flow_index.setdefault(ev.flow_id, []).append(ev.id)

    events_by_step: dict[str, list[int]] = {}
    for step in steps:
        events_by_step[step.id] = list(step.event_ids)

    return ParsedTrace(
        events=events,
        steps=steps,
        cpu_pid=cpu_pid,
        gpu_pids=gpu_pids,
        device_properties=meta.get("device_properties", []),
        trace_start_us=start,
        trace_end_us=end,
        trace_name=meta.get("trace_name"),
        events_by_step=events_by_step,
        correlation_to_runtime=correlation_to_runtime,
        flow_index=flow_index,
    )
