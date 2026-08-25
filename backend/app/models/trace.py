from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .event import TraceEvent
from .step import ExecutionStep


@dataclass
class ParsedTrace:
    events: list[TraceEvent]
    steps: list[ExecutionStep]
    cpu_pid: Optional[int]
    gpu_pids: list[int]
    device_properties: list[dict[str, Any]]
    trace_start_us: float
    trace_end_us: float
    trace_name: Optional[str] = None
    events_by_step: dict[str, list[int]] = field(default_factory=dict)
    correlation_to_runtime: dict[int, int] = field(default_factory=dict)
    flow_index: dict[int, list[int]] = field(default_factory=dict)

    def event(self, event_id: int) -> Optional[TraceEvent]:
        if 0 <= event_id < len(self.events):
            return self.events[event_id]
        return None

    def step(self, step_id: str) -> Optional[ExecutionStep]:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def flow_events_for(self, event: TraceEvent, limit: int = 20) -> list[TraceEvent]:
        if event.flow_id is None:
            return []
        result: list[TraceEvent] = []
        for event_id in self.flow_index.get(event.flow_id, []):
            if event_id == event.id:
                continue
            ev = self.event(event_id)
            if ev is not None:
                result.append(ev)
            if len(result) >= limit:
                break
        return result
