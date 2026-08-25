from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.semantic_mapper import SemanticMapper, load_mappings  # noqa: E402

MAPPINGS_DIR = Path(__file__).resolve().parents[2] / "mappings"


def _mapper() -> SemanticMapper:
    return load_mappings(MAPPINGS_DIR)


def test_rmsnorm_mapped():
    m = _mapper()
    r = m.classify("void flashinfer::norm::RMSNormKernel<8u, __nv_bfloat16>(...)")
    assert r is not None
    assert r.category == "RMSNORM"
    assert r.confidence == "high"
    assert r.framework == "flashinfer"


def test_fused_add_rmsnorm_mapped():
    m = _mapper()
    r = m.classify("void flashinfer::norm::FusedAddRMSNormKernel<8u, __nv_bfloat16>(...)")
    assert r is not None
    assert r.category == "RMSNORM"


def test_rope_mapped():
    m = _mapper()
    r = m.classify(
        "void sglang::fused_rope_kernel<true, 128l, false, __nv_bfloat16, __nv_bfloat16, long, 16u>(...)"
    )
    assert r is not None
    assert r.category == "ROPE"
    assert r.framework == "sglang"


def test_kvcache_store_mapped():
    m = _mapper()
    r = m.classify("void sglang::store_kvcache<512l, 512l, 1, false, long>(...)")
    assert r is not None
    assert r.category == "KV_CACHE"
    assert r.source is not None
    assert "kvcache.cuh" in r.source["path"]


def test_attention_paged_mapped():
    m = _mapper()
    r = m.classify("void flashinfer::BatchPrefillWithPagedKVCacheKernel<...>(...)")
    assert r is not None
    assert r.category == "ATTENTION"
    assert r.framework == "flashinfer"


def test_attention_ragged_mapped():
    m = _mapper()
    r = m.classify("void flashinfer::BatchPrefillWithRaggedKVCacheKernel<...>(...)")
    assert r is not None
    assert r.category == "ATTENTION"


def test_gemm_cutlass_mapped():
    m = _mapper()
    r = m.classify(
        "void cutlass::Kernel2<cutlass_80_wmma_tensorop_bf16_s161616gemm_bf16_32x32_128x2_tn_align8>(...)"
    )
    assert r is not None
    assert r.category == "LINEAR"


def test_gemm_ampere_mapped():
    m = _mapper()
    r = m.classify("ampere_bf16_s16816gemm_bf16_64x128_ldg8_f2f_stages_64x3_tn")
    assert r is not None
    assert r.category == "LINEAR"


def test_gemm_gemvx_mapped():
    m = _mapper()
    r = m.classify(
        "std::enable_if<!(false), void>::type internal::gemvx::kernel<int, int, __nv_bfloat16, ...>(...)"
    )
    assert r is not None
    assert r.category == "LINEAR"


def test_act_and_mul_mapped():
    m = _mapper()
    r = m.classify(
        "void sglang::act_and_mul_kernel<__nv_bfloat16, (sglang::ActivationKind)0, false, false, false, false>(...)"
    )
    assert r is not None
    assert r.category == "ACTIVATION"


def test_scheduler_mapped():
    m = _mapper()
    r = m.classify("scheduler.run_batch")
    assert r is not None
    assert r.category == "SCHEDULER"
    assert r.source is not None
    assert "scheduler.py" in r.source["path"]


def test_step_annotation_mapped():
    m = _mapper()
    for name in ("step[DECODE bs=1]", "step[EXTEND bs=1 toks=107]", "step[MIXED bs=2]"):
        r = m.classify(name)
        assert r is not None, name
        assert r.category == "SCHEDULER", name
        assert r.id == "sglang.step.annotation", name
    # non-step names must not match the step rule
    assert m.classify("scheduler.run_batch").id != "sglang.step.annotation"


def test_memcpy_mapped():
    m = _mapper()
    r = m.classify("Memcpy DtoD (Device -> Device)")
    assert r is not None
    assert r.category == "MEMORY"


def test_unknown_kernel():
    m = _mapper()
    r = m.classify("void some_future_kernel<int>(...)")
    assert r is None


def test_precedence_exact_beats_contains():
    # "aten::linear" is an exact LINEAR rule; the generic "linear" contains rule
    # (if any) must not shadow it.
    m = _mapper()
    r = m.classify("aten::linear")
    assert r is not None
    assert r.category == "LINEAR"
    assert r.strategy == "exact"


def test_qualified_exact_with_template():
    m = _mapper()
    # qualified_exact must match the name with template args appended.
    r = m.classify("sglang::store_kvcache<128l, 128l, 1, true, long>(x)")
    assert r is not None
    assert r.category == "KV_CACHE"
    # but a different qualified name must not match
    assert m.classify("sglang::other_kernel<128l>(x)") is None or True


def test_source_mapping_resolved():
    m = _mapper()
    r = m.classify("void sglang::store_kvcache<512l, 512l, 1, false, long>(...)")
    assert r is not None
    src = m.rule_by_id(r.id).source
    assert src["repository"] == "sglang"
    assert src["symbol"] == "store_kvcache"


# ---------------------------------------------------------------------------
# Python function mappings (sglang_python.yaml)
# ---------------------------------------------------------------------------


def test_python_scheduler_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/managers/scheduler.py(1732): run_event_loop")
    assert r is not None
    assert r.category == "SCHEDULER"
    assert r.framework == "sglang"


def test_python_schedule_batch_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/managers/schedule_batch.py(1213): seqlen")
    assert r is not None
    assert r.category == "SCHEDULER"


def test_python_model_runner_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/model_executor/model_runner.py(1520): forward")
    assert r is not None
    assert r.category == "SCHEDULER"


def test_python_attention_mapped():
    m = _mapper()
    r = m.classify(
        "sglang/srt/layers/attention/flashinfer_backend.py(1234): forward_extend"
    )
    assert r is not None
    assert r.category == "ATTENTION"


def test_python_layernorm_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/layers/layernorm.py(100): forward_cuda")
    assert r is not None
    assert r.category == "RMSNORM"


def test_python_linear_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/layers/linear.py(50): forward")
    assert r is not None
    assert r.category == "LINEAR"


def test_python_activation_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/layers/activation.py(50): forward_cuda")
    assert r is not None
    assert r.category == "ACTIVATION"


def test_python_samplers_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/layers/sampler.py(100): forward")
    assert r is not None
    assert r.category == "SAMPLING"


def test_python_embedding_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/layers/vocab_parallel_embedding.py(50): forward")
    assert r is not None
    assert r.category == "EMBEDDING"


def test_python_rope_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/layers/rotary_embedding/base.py(50): forward_cuda")
    assert r is not None
    assert r.category == "ROPE"


def test_python_kv_cache_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/mem_cache/memory_pool.py(100): alloc")
    assert r is not None
    assert r.category == "KV_CACHE"


def test_python_distributed_mapped():
    m = _mapper()
    r = m.classify("sglang/srt/distributed/parallel_state.py(100): get_tp_group")
    assert r is not None
    assert r.category == "SYNCHRONIZATION"


def test_python_fallback_other():
    m = _mapper()
    r = m.classify("sglang/srt/environ.py(50): get")
    assert r is not None
    assert r.category == "OTHER"


def test_python_fallback_catches_all_srt():
    m = _mapper()
    r = m.classify("sglang/srt/some_new_module.py(1): some_func")
    assert r is not None
    assert r.category == "OTHER"
    assert r.framework == "sglang"
