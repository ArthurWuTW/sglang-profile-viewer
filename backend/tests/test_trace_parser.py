from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.trace_parser import (  # noqa: E402
    TraceParseError,
    build_trace,
    detect_pids,
    normalize_events,
    read_trace_file,
)


def _write_gz(path: Path, obj) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f)


def test_read_and_normalize(tmp_path):
    trace = {
        "traceEvents": [
            {"ph": "M", "name": "process_labels", "ts": 0, "pid": 1, "tid": 0,
             "args": {"labels": "CPU"}},
            {"ph": "X", "name": "foo_kernel", "cat": "kernel", "ts": 100.0,
             "dur": 10.0, "pid": 0, "tid": 5, "args": {"correlation": 7}},
            {"ph": "X", "name": "cudaLaunchKernel", "cat": "cuda_runtime",
             "ts": 90.0, "dur": 5.0, "pid": 1, "tid": 1,
             "args": {"correlation": 7, "External id": 3}},
        ]
    }
    p = tmp_path / "t.json.gz"
    _write_gz(p, trace)
    data = read_trace_file(p)
    events, meta = normalize_events(data)
    assert len(events) == 3
    kern = events[1]
    assert kern.raw_name == "foo_kernel"
    assert kern.category == "kernel"
    assert kern.timestamp_us == 100.0
    assert kern.duration_us == 10.0
    assert kern.end_us == 110.0
    assert kern.args["correlation"] == 7
    # raw reconstruction is lossless for the fields we keep
    raw = kern.to_raw()
    assert raw["name"] == "foo_kernel"
    assert raw["cat"] == "kernel"
    assert raw["ts"] == 100.0
    assert raw["dur"] == 10.0
    assert raw["args"]["correlation"] == 7
    cpu_pid, gpu_pids = detect_pids(events)
    assert cpu_pid == 1
    assert gpu_pids == []


def test_detect_pids_fallback(tmp_path):
    # No process_labels metadata -> fallback to most-events pid.
    events_raw = [
        {"ph": "X", "name": "a", "cat": "cpu_op", "ts": 0, "dur": 1, "pid": 5, "tid": 1},
        {"ph": "X", "name": "b", "cat": "cpu_op", "ts": 1, "dur": 1, "pid": 5, "tid": 1},
        {"ph": "X", "name": "c", "cat": "kernel", "ts": 2, "dur": 1, "pid": 0, "tid": 1},
    ]
    data = {"traceEvents": events_raw}
    events, _ = normalize_events(data)
    cpu_pid, _ = detect_pids(events)
    assert cpu_pid == 5


def test_invalid_gzip_is_temporary(tmp_path):
    p = tmp_path / "bad.json.gz"
    p.write_bytes(b"\x01\x02\x03not gzip")
    with pytest.raises(TraceParseError) as exc:
        read_trace_file(p)
    assert exc.value.temporary is True


def test_invalid_json_is_temporary(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(TraceParseError) as exc:
        read_trace_file(p)
    assert exc.value.temporary is True


def test_missing_traceevents_is_permanent(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"foo": 1}', encoding="utf-8")
    with pytest.raises(TraceParseError) as exc:
        read_trace_file(p)
    assert exc.value.temporary is False


def test_build_trace_indexes():
    trace = {
        "traceEvents": [
            {"ph": "M", "name": "process_labels", "ts": 0, "pid": 1, "tid": 0,
             "args": {"labels": "CPU"}},
            {"ph": "X", "name": "k", "cat": "kernel", "ts": 100.0, "dur": 10.0,
             "pid": 0, "tid": 5, "args": {"correlation": 7}},
            {"ph": "X", "name": "cudaLaunchKernel", "cat": "cuda_runtime",
             "ts": 90.0, "dur": 5.0, "pid": 1, "tid": 1,
             "args": {"correlation": 7, "External id": 3}},
            {"ph": "s", "id": 42, "name": "ac2g", "cat": "ac2g", "ts": 90.0,
             "pid": 1, "tid": 1},
            {"ph": "f", "id": 42, "name": "ac2g", "cat": "ac2g", "ts": 100.0,
             "pid": 0, "tid": 5, "bp": "e"},
        ]
    }
    events, meta = normalize_events(trace)
    cpu_pid, gpu_pids = detect_pids(events)
    t = build_trace(events, meta, steps=[], cpu_pid=cpu_pid, gpu_pids=gpu_pids)
    assert t.correlation_to_runtime[7] == 2
    assert t.flow_index[42] == [3, 4]
    assert t.trace_start_us == 90.0
    assert t.trace_end_us == 110.0
