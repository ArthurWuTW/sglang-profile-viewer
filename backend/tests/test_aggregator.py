from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.event import TraceEvent  # noqa: E402
from app.models.step import ExecutionStep  # noqa: E402
from app.services.aggregator import _union_duration, aggregate_step  # noqa: E402


def _kern(i, name, ts, dur, cat="kernel", semantic=None):
    ev = TraceEvent(
        id=i,
        raw_name=name,
        category=cat,
        phase="X",
        timestamp_us=ts,
        duration_us=dur,
        process_id=0,
        thread_id=5,
        args={},
    )
    ev.semantic_category = semantic
    return ev


def test_union_duration_disjoint():
    assert _union_duration([(0, 10), (20, 30)]) == 20.0


def test_union_duration_overlap():
    assert _union_duration([(0, 10), (5, 15)]) == 15.0


def test_union_duration_nested():
    assert _union_duration([(0, 100), (10, 20)]) == 100.0


def test_union_duration_empty():
    assert _union_duration([]) == 0.0


def test_aggregate_step_metrics():
    step = ExecutionStep(
        id="step-1",
        index=1,
        stage="DECODE",
        batch_size=1,
        tokens=None,
        start_us=1000.0,
        duration_us=5000.0,
    )
    events = [
        _kern(0, "rmsnorm", 1100.0, 100.0, semantic="RMSNORM"),
        _kern(1, "rope", 1200.0, 80.0, semantic="ROPE"),
        _kern(2, "attn", 1300.0, 400.0, semantic="ATTENTION"),
        _kern(3, "unknown", 2000.0, 50.0, semantic="UNKNOWN"),
        _kern(4, "memcpy", 3000.0, 30.0, cat="gpu_memcpy", semantic="MEMORY"),
        # overlapping kernel on another stream
        _kern(5, "attn2", 1350.0, 200.0, semantic="ATTENTION"),
    ]
    m = aggregate_step(step, events)
    assert m["wallDurationUs"] == 5000.0
    # union of GPU intervals: [1100,1200] [1200,1280] [1300,1700] [2000,2050]
    # [3000,3030] -> 100 + 80 + 400 + 50 + 30 = 660 (attn2 nested in attn)
    assert m["gpuBusyUs"] == 660.0
    assert m["gpuKernelCount"] == 5  # kernel cat only (not memcpy)
    assert m["unknownCount"] == 1
    assert m["semanticDurationByCategory"]["ATTENTION"] == 600.0  # 400 + 200 (sum, not union)
    assert m["semanticDurationByCategory"]["RMSNORM"] == 100.0
    assert m["topKernels"][0]["name"] == "attn"
    assert m["topKernels"][0]["totalUs"] == 400.0
