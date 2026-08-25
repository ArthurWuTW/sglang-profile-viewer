from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TraceEvent:
    id: int
    raw_name: str
    category: Optional[str]
    phase: Optional[str]
    timestamp_us: float
    duration_us: Optional[float]
    process_id: Optional[int]
    thread_id: Optional[int]
    args: dict = field(default_factory=dict)
    flow_id: Optional[int] = None

    semantic_category: Optional[str] = None
    semantic_name: Optional[str] = None
    confidence: Optional[str] = None
    framework: Optional[str] = None
    rule_id: Optional[str] = None
    step_id: Optional[str] = None
    parent_event_id: Optional[str] = None

    @property
    def name(self) -> str:
        return self.semantic_name or self.raw_name

    @property
    def end_us(self) -> float:
        if self.duration_us is None:
            return self.timestamp_us
        return self.timestamp_us + self.duration_us

    def to_raw(self) -> dict[str, Any]:
        raw: dict[str, Any] = {
            "ph": self.phase,
            "name": self.raw_name,
            "cat": self.category,
            "ts": self.timestamp_us,
            "pid": self.process_id,
            "tid": self.thread_id,
            "args": self.args,
        }
        if self.duration_us is not None:
            raw["dur"] = self.duration_us
        if self.flow_id is not None:
            raw["id"] = self.flow_id
        return raw

    def to_dict(self, relative_to: Optional[float] = None) -> dict[str, Any]:
        ts = self.timestamp_us
        if relative_to is not None:
            ts = self.timestamp_us - relative_to
        return {
            "id": str(self.id),
            "name": self.name,
            "rawName": self.raw_name,
            "category": self.category,
            "phase": self.phase,
            "ts": ts,
            "dur": self.duration_us,
            "pid": self.process_id,
            "tid": self.thread_id,
            "semanticCategory": self.semantic_category,
            "semanticName": self.semantic_name,
            "confidence": self.confidence,
            "framework": self.framework,
            "ruleId": self.rule_id,
            "stepId": self.step_id,
            "flowId": self.flow_id,
        }

    def to_compact(self, relative_to: Optional[float] = None) -> dict[str, Any]:
        ts = self.timestamp_us
        if relative_to is not None:
            ts = self.timestamp_us - relative_to
        return {
            "id": str(self.id),
            "name": self.name,
            "rawName": self.raw_name,
            "category": self.semantic_category or "UNKNOWN",
            "confidence": self.confidence,
            "framework": self.framework,
            "kind": self.category or "unknown",
            "ts": ts,
            "dur": self.duration_us,
            "pid": self.process_id,
            "tid": self.thread_id,
        }
