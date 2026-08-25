from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.event import TraceEvent  # noqa: E402
from app.services.step_detector import (  # noqa: E402
    attribute_events_to_steps,
    detect_steps,
    parse_step_name,
)


def test_parse_step_name_decode():
    r = parse_step_name("step[DECODE bs=1]")
    assert r == {"stage": "DECODE", "batch_size": 1, "tokens": None}


def test_parse_step_name_extend():
    r = parse_step_name("step[EXTEND bs=1 toks=107]")
    assert r == {"stage": "EXTEND", "batch_size": 1, "tokens": 107}


def test_parse_step_name_mixed():
    r = parse_step_name("step[MIXED bs=2]")
    assert r == {"stage": "MIXED", "batch_size": 2, "tokens": None}


def test_parse_step_name_unknown_stage():
    r = parse_step_name("step[WEIRD bs=3]")
    assert r["stage"] == "UNKNOWN"
    assert r["batch_size"] == 3


def test_parse_step_name_not_a_step():
    assert parse_step_name("scheduler.run_batch") is None
    assert parse_step_name("step[") is None


def _ev(i, name, cat, ts, dur, pid, tid, args=None):
    return TraceEvent(
        id=i,
        raw_name=name,
        category=cat,
        phase="X",
        timestamp_us=ts,
        duration_us=dur,
        process_id=pid,
        thread_id=tid,
        args=args or {},
    )


def test_detect_steps_and_attribution():
    events = [
        _ev(0, "step[DECODE bs=1]", "user_annotation", 1000.0, 5000.0, 1, 1),
        _ev(1, "aten::linear", "cpu_op", 1100.0, 100.0, 1, 1),
        _ev(2, "cudaLaunchKernel", "cuda_runtime", 1120.0, 20.0, 1, 1,
            {"correlation": 100}),
        # GPU kernel executes AFTER the step ends (async) but was launched
        # inside it -> must be attributed via correlation, not its own ts.
        _ev(3, "some_kernel", "kernel", 7000.0, 100.0, 0, 5, {"correlation": 100}),
        # GPU kernel launched outside any step -> unattributed.
        _ev(4, "cudaLaunchKernel", "cuda_runtime", 9000.0, 20.0, 1, 1,
            {"correlation": 200}),
        _ev(5, "other_kernel", "kernel", 9100.0, 100.0, 0, 5, {"correlation": 200}),
    ]
    steps = detect_steps(events, cpu_pid=1)
    assert len(steps) == 1
    step = steps[0]
    assert step.stage == "DECODE"
    assert step.batch_size == 1
    assert step.start_us == 1000.0
    assert step.duration_us == 5000.0
    assert step.id == "step-1"

    attribute_events_to_steps(events, steps, cpu_pid=1)
    # step annotation + cpu op + launch + async kernel all attributed
    assert events[0].step_id == "step-1"
    assert events[1].step_id == "step-1"
    assert events[2].step_id == "step-1"
    assert events[3].step_id == "step-1"
    # kernel launched outside the step is NOT attributed
    assert events[5].step_id is None
    assert set(step.event_ids) == {0, 1, 2, 3}


def test_multiple_steps_numbered_chronologically():
    events = [
        _ev(0, "step[DECODE bs=1]", "user_annotation", 2000.0, 100.0, 1, 1),
        _ev(1, "step[EXTEND bs=1 toks=4]", "user_annotation", 1000.0, 100.0, 1, 1),
    ]
    steps = detect_steps(events, cpu_pid=1)
    assert [s.id for s in steps] == ["step-1", "step-2"]
    assert steps[0].stage == "EXTEND"
    assert steps[1].stage == "DECODE"
