from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

STAGES = ("PREFILL", "DECODE", "EXTEND", "MIXED", "IDLE", "UNKNOWN")


@dataclass
class ExecutionStep:
    id: str
    index: int
    stage: str
    batch_size: Optional[int]
    tokens: Optional[int]
    start_us: float
    duration_us: float
    raw_name: str = ""
    event_ids: list[int] = field(default_factory=list)

    @property
    def end_us(self) -> float:
        return self.start_us + self.duration_us

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "index": self.index,
            "stage": self.stage,
            "batchSize": self.batch_size,
            "tokens": self.tokens,
            "startUs": self.start_us,
            "durationUs": self.duration_us,
            "endUs": self.end_us,
            "eventCount": len(self.event_ids),
            "rawName": self.raw_name,
        }
