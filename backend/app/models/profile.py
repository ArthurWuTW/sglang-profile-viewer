from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .trace import ParsedTrace


class ProfileStatus(str, Enum):
    DISCOVERED = "discovered"
    PARSING = "parsing"
    READY = "ready"
    FAILED = "failed"
    FAILED_TEMPORARY = "failed_temporary"
    REMOVED = "removed"


@dataclass
class ProfileRecord:
    id: str
    path: str
    size_bytes: int
    mtime: float
    status: ProfileStatus = ProfileStatus.DISCOVERED
    error: Optional[str] = None
    discovered_at: float = 0.0
    parsed_at: Optional[float] = None
    event_count: int = 0
    step_count: int = 0
    trace_start_us: Optional[float] = None
    trace_end_us: Optional[float] = None
    trace: Optional[ParsedTrace] = field(default=None, repr=False)

    @property
    def file_name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def run_timestamp(self) -> Optional[float]:
        parent = self.path.rsplit("/", 1)[0].rsplit("/", 1)[-1]
        try:
            return float(parent)
        except ValueError:
            return None

    def to_summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "fileName": self.file_name,
            "sizeBytes": self.size_bytes,
            "status": self.status.value,
            "error": self.error,
            "createdAt": self.mtime,
            "runTimestamp": self.run_timestamp,
            "eventCount": self.event_count,
            "stepCount": self.step_count,
            "traceStartUs": self.trace_start_us,
            "traceEndUs": self.trace_end_us,
        }
