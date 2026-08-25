"""Generate a small synthetic golden trace for regression tests.

Produces a Chrome-trace JSON (gzipped) that mimics the structure of a real
SGLang `bench_serving --profile` output:
  - process metadata (CPU + GPU labels)
  - step[DECODE bs=1] / step[EXTEND bs=1 toks=4] user_annotation spans
  - GPU kernels with correlation ids
  - cuda_runtime launch events carrying the same correlation ids
  - cpu_op events on the CPU pid
  - ac2g flow events

Run:  python3 scripts/make_golden_fixture.py
Output: fixtures/profile/golden/golden-trace.json.gz
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

CPU_PID = 100
GPU_PID = 0
CPU_TID = 100
GPU_TID = 7

# Base timestamp (us)
T0 = 1_000_000.0


def X(name, cat, ts, dur, pid, tid, args=None):
    e = {
        "ph": "X",
        "name": name,
        "cat": cat,
        "ts": ts,
        "dur": dur,
        "pid": pid,
        "tid": tid,
        "args": args or {},
    }
    return e


def M(name, pid, tid, args):
    return {"ph": "M", "name": name, "ts": T0, "pid": pid, "tid": tid, "args": args}


def build_events():
    ev = []
    # --- process metadata ---
    ev.append(M("process_name", CPU_PID, 0, {"name": "sglang::scheduler"}))
    ev.append(M("process_labels", CPU_PID, 0, {"labels": "CPU"}))
    ev.append(M("process_name", GPU_PID, 0, {"name": "sglang::scheduler"}))
    ev.append(M("process_labels", GPU_PID, 0, {"labels": "GPU 0"}))

    # --- DECODE step (bs=1) ---
    decode_start = T0 + 1000.0
    decode_dur = 5000.0
    ev.append(
        X("step[DECODE bs=1]", "user_annotation", decode_start, decode_dur, CPU_PID, CPU_TID,
          {"External id": 1})
    )
    # scheduler.run_batch contains the step
    ev.append(
        X("scheduler.run_batch", "user_annotation", decode_start - 200.0, decode_dur + 400.0,
          CPU_PID, CPU_TID, {"External id": 0})
    )
    # CPU ops inside the step
    ev.append(X("aten::linear", "cpu_op", decode_start + 100.0, 300.0, CPU_PID, CPU_TID,
                {"External id": 10}))
    ev.append(X("aten::add", "cpu_op", decode_start + 450.0, 50.0, CPU_PID, CPU_TID,
                {"External id": 11}))
    # cuda_runtime launches (correlation ids 100, 101, 102, 103)
    ev.append(X("cudaLaunchKernel", "cuda_runtime", decode_start + 120.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 10, "correlation": 100}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", decode_start + 500.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 11, "correlation": 101}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", decode_start + 900.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 12, "correlation": 102}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", decode_start + 1500.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 13, "correlation": 103}))
    # GPU kernels (execute asynchronously, may extend past the step)
    ev.append(X("void flashinfer::norm::RMSNormKernel<8u, __nv_bfloat16>(...)", "kernel",
                decode_start + 200.0, 100.0, GPU_PID, GPU_TID, {"correlation": 100}))
    ev.append(X("void sglang::fused_rope_kernel<true, 128l, false, __nv_bfloat16, __nv_bfloat16, long, 16u>(...)",
                "kernel", decode_start + 600.0, 80.0, GPU_PID, GPU_TID, {"correlation": 101}))
    ev.append(X("void sglang::store_kvcache<512l, 512l, 1, false, long>(...)", "kernel",
                decode_start + 1000.0, 60.0, GPU_PID, GPU_TID, {"correlation": 102}))
    ev.append(X("void flashinfer::BatchPrefillWithPagedKVCacheKernel<...>(...)", "kernel",
                decode_start + 1600.0, 400.0, GPU_PID, GPU_TID, {"correlation": 103}))
    # an unknown kernel
    ev.append(X("void some_future_kernel<int>(...)", "kernel",
                decode_start + 2100.0, 50.0, GPU_PID, GPU_TID, {"correlation": 104}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", decode_start + 2050.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 14, "correlation": 104}))
    # a GEMM kernel (cutlass)
    ev.append(X("void cutlass::Kernel2<cutlass_80_wmma_tensorop_bf16_s161616gemm_bf16_32x32_128x2_tn_align8>(...)",
                "kernel", decode_start + 2500.0, 300.0, GPU_PID, GPU_TID, {"correlation": 105}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", decode_start + 2450.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 15, "correlation": 105}))
    # act_and_mul (MLP activation)
    ev.append(X("void sglang::act_and_mul_kernel<__nv_bfloat16, (sglang::ActivationKind)0, false, false, false, false>(...)",
                "kernel", decode_start + 3000.0, 120.0, GPU_PID, GPU_TID, {"correlation": 106}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", decode_start + 2950.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 16, "correlation": 106}))
    # a memcpy
    ev.append(X("Memcpy DtoD (Device -> Device)", "gpu_memcpy",
                decode_start + 3300.0, 30.0, GPU_PID, GPU_TID, {"correlation": 107}))
    ev.append(X("cudaMemcpyAsync", "cuda_runtime", decode_start + 3250.0, 15.0,
                CPU_PID, CPU_TID, {"External id": 17, "correlation": 107}))

    # --- EXTEND step (bs=1, toks=4) ---
    extend_start = decode_start + decode_dur + 1000.0
    extend_dur = 8000.0
    ev.append(
        X("step[EXTEND bs=1 toks=4]", "user_annotation", extend_start, extend_dur,
          CPU_PID, CPU_TID, {"External id": 20})
    )
    ev.append(X("aten::linear", "cpu_op", extend_start + 100.0, 400.0, CPU_PID, CPU_TID,
                {"External id": 30}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", extend_start + 120.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 30, "correlation": 200}))
    ev.append(X("void flashinfer::norm::FusedAddRMSNormKernel<8u, __nv_bfloat16>(...)", "kernel",
                extend_start + 200.0, 150.0, GPU_PID, GPU_TID, {"correlation": 200}))
    ev.append(X("cudaLaunchKernel", "cuda_runtime", extend_start + 800.0, 20.0,
                CPU_PID, CPU_TID, {"External id": 31, "correlation": 201}))
    ev.append(X("void flashinfer::BatchPrefillWithRaggedKVCacheKernel<...>(...)", "kernel",
                extend_start + 900.0, 2000.0, GPU_PID, GPU_TID, {"correlation": 201}))

    # --- ac2g flow events (CPU -> GPU correlation) ---
    for corr in (100, 101, 102, 103, 104, 105, 106, 107, 200, 201):
        ev.append({"ph": "s", "id": corr, "pid": CPU_PID, "tid": CPU_TID,
                   "ts": T0, "cat": "ac2g", "name": "ac2g"})
        ev.append({"ph": "f", "id": corr, "pid": GPU_PID, "tid": GPU_TID,
                   "ts": T0, "cat": "ac2g", "name": "ac2g", "bp": "e"})

    return ev


def main():
    out = Path(__file__).resolve().parents[1] / "fixtures" / "profile" / "golden" / "golden-trace.json.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    trace = {
        "schemaVersion": 1,
        "deviceProperties": [
            {"id": 0, "name": "NVIDIA Fake GPU", "totalGlobalMem": 16000000000,
             "computeMajor": 8, "computeMinor": 9, "numSms": 34}
        ],
        "traceEvents": build_events(),
        "traceName": "golden-trace.json",
    }
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(trace, f)
    print(f"Wrote {out} ({len(trace['traceEvents'])} events)")


if __name__ == "__main__":
    main()
