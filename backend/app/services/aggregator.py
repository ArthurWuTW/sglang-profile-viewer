from __future__ import annotations

from typing import Any

from ..models.event import TraceEvent
from ..models.step import ExecutionStep

# Event categories that represent actual GPU work.
GPU_CATEGORIES = ("kernel", "gpu_memcpy", "gpu_memset")


def _union_duration(intervals: list[tuple[float, float]]) -> float:
    """Total length of the union of [start, end) intervals."""
    if not intervals:
        return 0.0
    intervals.sort()
    total = 0.0
    cur_s, cur_e = intervals[0]
    for s, e in intervals[1:]:
        if s > cur_e:
            total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    total += cur_e - cur_s
    return total


def aggregate_step(
    step: ExecutionStep, events: list[TraceEvent]
) -> dict[str, Any]:
    """Compute per-step metrics.

    Important: ``semanticDurationByCategory`` is the *sum* of per-category GPU
    event durations. Because GPU events on different streams may overlap, the
    sum can exceed ``wallDurationUs``. ``gpuBusyUs`` is the union of all GPU
    intervals (true busy time).
    """
    gpu_events = [ev for ev in events if ev.category in GPU_CATEGORIES]

    gpu_intervals = [
        (ev.timestamp_us, ev.end_us)
        for ev in gpu_events
        if ev.duration_us is not None and ev.duration_us > 0
    ]
    gpu_busy_us = _union_duration(gpu_intervals)

    semantic_duration: dict[str, float] = {}
    kernel_count = 0
    unknown_count = 0
    kernel_totals: dict[str, dict[str, float]] = {}

    for ev in gpu_events:
        if ev.category == "kernel":
            kernel_count += 1
        cat = ev.semantic_category or "UNKNOWN"
        if cat == "UNKNOWN":
            unknown_count += 1
        dur = ev.duration_us or 0.0
        semantic_duration[cat] = semantic_duration.get(cat, 0.0) + dur
        bucket = kernel_totals.setdefault(
            ev.raw_name, {"count": 0.0, "totalUs": 0.0}
        )
        bucket["count"] += 1
        bucket["totalUs"] += dur

    top_kernels = sorted(
        (
            {"name": name, "count": int(v["count"]), "totalUs": v["totalUs"]}
            for name, v in kernel_totals.items()
        ),
        key=lambda k: k["totalUs"],
        reverse=True,
    )[:5]

    return {
        "wallDurationUs": step.duration_us,
        "gpuBusyUs": gpu_busy_us,
        "gpuKernelCount": kernel_count,
        "unknownCount": unknown_count,
        "semanticDurationByCategory": semantic_duration,
        "topKernels": top_kernels,
    }


def find_context_events(
    trace, step: ExecutionStep, limit: int = 10
) -> list[TraceEvent]:
    """CPU scheduler annotations that fully contain the step (e.g. scheduler.run_batch).

    Only ``user_annotation`` events are considered so that long-running
    background python_function frames (threading, watchdog, etc.) are not
    reported as step context.
    """
    result: list[TraceEvent] = []
    for ev in trace.events:
        if ev.process_id != trace.cpu_pid:
            continue
        if ev.category != "user_annotation":
            continue
        if ev.duration_us is None:
            continue
        if ev.id in step.event_ids:
            continue
        if ev.timestamp_us <= step.start_us and ev.end_us >= step.end_us:
            result.append(ev)
    result.sort(key=lambda e: e.duration_us or 0.0, reverse=True)
    return result[:limit]
