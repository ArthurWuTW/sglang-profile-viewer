from __future__ import annotations

# Semantic category taxonomy.
#
# This is the canonical list of semantic categories the viewer can classify
# profiler events into. It is the single source of truth for the backend and is
# exposed to the frontend via GET /api/categories. The frontend keeps a matching
# color palette (frontend/src/utils/colors.ts).
#
# The taxonomy is intentionally broader than the set of categories that have
# mapping rules today; categories with no rules simply never appear in a trace.
CATEGORY_TAXONOMY = [
    {"id": "SCHEDULER", "displayName": "Scheduler", "group": "Scheduler"},
    {"id": "EMBEDDING", "displayName": "Embedding", "group": "Embedding"},
    {"id": "RMSNORM", "displayName": "RMSNorm", "group": "Normalization"},
    {"id": "ROPE", "displayName": "RoPE", "group": "Position Encoding"},
    {"id": "QKV_PROJECTION", "displayName": "QKV Projection", "group": "Linear/GEMM"},
    {"id": "Q_PROJECTION", "displayName": "Q Projection", "group": "Linear/GEMM"},
    {"id": "K_PROJECTION", "displayName": "K Projection", "group": "Linear/GEMM"},
    {"id": "V_PROJECTION", "displayName": "V Projection", "group": "Linear/GEMM"},
    {"id": "O_PROJECTION", "displayName": "O Projection", "group": "Linear/GEMM"},
    {"id": "ATTENTION", "displayName": "Attention", "group": "Attention"},
    {"id": "KV_CACHE", "displayName": "KV Cache", "group": "KV Cache"},
    {"id": "LINEAR", "displayName": "GEMM / Linear", "group": "Linear/GEMM"},
    {"id": "MLP", "displayName": "MLP", "group": "MLP"},
    {"id": "ACTIVATION", "displayName": "Activation", "group": "MLP"},
    {"id": "SAMPLING", "displayName": "Sampling", "group": "Sampling"},
    {"id": "MEMORY", "displayName": "Memory", "group": "Memory"},
    {"id": "SYNCHRONIZATION", "displayName": "Synchronization", "group": "Synchronization"},
    {"id": "OTHER", "displayName": "Other", "group": "Other"},
    {"id": "UNKNOWN", "displayName": "Unknown", "group": "Other"},
]

# Display order for timeline rows (categories not listed fall to the end).
CATEGORY_ROW_ORDER = [
    "SCHEDULER",
    "EMBEDDING",
    "RMSNORM",
    "ROPE",
    "QKV_PROJECTION",
    "Q_PROJECTION",
    "K_PROJECTION",
    "V_PROJECTION",
    "O_PROJECTION",
    "ATTENTION",
    "KV_CACHE",
    "LINEAR",
    "MLP",
    "ACTIVATION",
    "SAMPLING",
    "MEMORY",
    "SYNCHRONIZATION",
    "OTHER",
    "UNKNOWN",
]
