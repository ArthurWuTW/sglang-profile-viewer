from __future__ import annotations

import re
from typing import Optional

from ..models.event import TraceEvent
from ..models.step import ExecutionStep

# Matches: step[DECODE bs=1], step[EXTEND bs=1 toks=107], step[MIXED bs=2], ...
STEP_RE = re.compile(r"^step\[\s*(?P<stage>[A-Z_]+)\s*(?P<attrs>[^\]]*)\]$")
BS_RE = re.compile(r"\bbs=(\d+)")
TOKS_RE = re.compile(r"\btoks=(\d+)")

# ForwardMode names from sglang.srt.model_executor.forward_batch_info.ForwardMode
KNOWN_STAGES = {
    "PREFILL",
    "DECODE",
    "EXTEND",
    "MIXED",
    "IDLE",
    "TARGET_VERIFY",
    "DRAFT_EXTEND_V2",
    "DRAFT_DECODE",
    "SPLIT_PREFILL",
    "DLLM_EXTEND",
}


def parse_step_name(name: str) -> Optional[dict]:
    """Parse a ``step[STAGE bs=N toks=M]`` annotation name.

    Returns a dict with ``stage``, ``batch_size``, ``tokens`` or None if the
    name is not a step annotation.
    """
    m = STEP_RE.match(name)
    if not m:
        return None
    stage = m.group("stage")
    attrs = m.group("attrs") or ""
    bs_m = BS_RE.search(attrs)
    toks_m = TOKS_RE.search(attrs)
    return {
        "stage": stage if stage in KNOWN_STAGES else "UNKNOWN",
        "batch_size": int(bs_m.group(1)) if bs_m else None,
        "tokens": int(toks_m.group(1)) if toks_m else None,
    }


def detect_steps(
    events: list[TraceEvent], cpu_pid: Optional[int]
) -> list[ExecutionStep]:
    """Find ``step[...]`` user_annotation events on the CPU pid and build steps.

    Steps are numbered in chronological order (1-based).
    """
    candidates = []
    for ev in events:
        if ev.category != "user_annotation" or ev.phase != "X":
            continue
        if cpu_pid is not None and ev.process_id != cpu_pid:
            continue
        if ev.duration_us is None:
            continue
        parsed = parse_step_name(ev.raw_name)
        if parsed is None:
            continue
        candidates.append((ev, parsed))

    candidates.sort(key=lambda p: p[0].timestamp_us)
    steps: list[ExecutionStep] = []
    for i, (ev, parsed) in enumerate(candidates, start=1):
        steps.append(
            ExecutionStep(
                id=f"step-{i}",
                index=i,
                stage=parsed["stage"],
                batch_size=parsed["batch_size"],
                tokens=parsed["tokens"],
                start_us=ev.timestamp_us,
                duration_us=ev.duration_us,
                raw_name=ev.raw_name,
                event_ids=[ev.id],
            )
        )
    return steps


def attribute_events_to_steps(
    events: list[TraceEvent], steps: list[ExecutionStep], cpu_pid: Optional[int]
) -> None:
    """Attribute events to steps in-place.

    CPU-side events are attributed by timestamp containment on the CPU pid.
    GPU events (kernel / gpu_memcpy / gpu_memset) are attributed through the
    correlation id to the cuda_runtime launch event, whose timestamp lies on the
    CPU thread inside the step window. This avoids mis-attributing asynchronous
    GPU work that executes after the launching step has ended.
    """
    import bisect

    if not steps:
        return

    # correlation id -> cuda_runtime event
    corr_map: dict[int, TraceEvent] = {}
    for ev in events:
        if ev.category == "cuda_runtime" and ev.phase == "X":
            corr = ev.args.get("correlation")
            if isinstance(corr, int):
                corr_map[corr] = ev

    steps_sorted = sorted(steps, key=lambda s: s.start_us)
    starts = [s.start_us for s in steps_sorted]

    def find_step(ts: float) -> Optional[ExecutionStep]:
        i = bisect.bisect_right(starts, ts) - 1
        if i < 0:
            return None
        s = steps_sorted[i]
        if ts < s.end_us:
            return s
        return None

    for ev in events:
        if ev.category in ("kernel", "gpu_memcpy", "gpu_memset"):
            corr = ev.args.get("correlation")
            launch = corr_map.get(corr) if isinstance(corr, int) else None
            if launch is None:
                continue
            step = find_step(launch.timestamp_us)
            if step is not None:
                ev.step_id = step.id
                step.event_ids.append(ev.id)
        else:
            if ev.process_id != cpu_pid:
                continue
            if ev.duration_us is None:
                continue
            step = find_step(ev.timestamp_us)
            if step is not None:
                ev.step_id = step.id
                step.event_ids.append(ev.id)
