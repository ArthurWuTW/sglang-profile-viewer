export interface CategoryStyle {
  id: string;
  displayName: string;
  color: string;
  group: string;
}

export const CATEGORY_STYLES: Record<string, CategoryStyle> = {
  SCHEDULER: { id: 'SCHEDULER', displayName: 'Scheduler', color: '#6b7280', group: 'Scheduler' },
  EMBEDDING: { id: 'EMBEDDING', displayName: 'Embedding', color: '#a855f7', group: 'Embedding' },
  RMSNORM: { id: 'RMSNORM', displayName: 'RMSNorm', color: '#f97316', group: 'Normalization' },
  ROPE: { id: 'ROPE', displayName: 'RoPE', color: '#eab308', group: 'Position Encoding' },
  QKV_PROJECTION: { id: 'QKV_PROJECTION', displayName: 'QKV Projection', color: '#3b82f6', group: 'Linear/GEMM' },
  Q_PROJECTION: { id: 'Q_PROJECTION', displayName: 'Q Projection', color: '#60a5fa', group: 'Linear/GEMM' },
  K_PROJECTION: { id: 'K_PROJECTION', displayName: 'K Projection', color: '#2563eb', group: 'Linear/GEMM' },
  V_PROJECTION: { id: 'V_PROJECTION', displayName: 'V Projection', color: '#1d4ed8', group: 'Linear/GEMM' },
  O_PROJECTION: { id: 'O_PROJECTION', displayName: 'O Projection', color: '#818cf8', group: 'Linear/GEMM' },
  ATTENTION: { id: 'ATTENTION', displayName: 'Attention', color: '#ef4444', group: 'Attention' },
  KV_CACHE: { id: 'KV_CACHE', displayName: 'KV Cache', color: '#22c55e', group: 'KV Cache' },
  LINEAR: { id: 'LINEAR', displayName: 'GEMM / Linear', color: '#6366f1', group: 'Linear/GEMM' },
  MLP: { id: 'MLP', displayName: 'MLP', color: '#ec4899', group: 'MLP' },
  ACTIVATION: { id: 'ACTIVATION', displayName: 'Activation', color: '#14b8a6', group: 'MLP' },
  SAMPLING: { id: 'SAMPLING', displayName: 'Sampling', color: '#d946ef', group: 'Sampling' },
  MEMORY: { id: 'MEMORY', displayName: 'Memory', color: '#06b6d4', group: 'Memory' },
  SYNCHRONIZATION: { id: 'SYNCHRONIZATION', displayName: 'Synchronization', color: '#94a3b8', group: 'Synchronization' },
  OTHER: { id: 'OTHER', displayName: 'Other', color: '#4b5563', group: 'Other' },
  UNKNOWN: { id: 'UNKNOWN', displayName: 'Unknown', color: '#374151', group: 'Other' },
};

export const CATEGORY_ROW_ORDER = [
  'SCHEDULER',
  'EMBEDDING',
  'RMSNORM',
  'ROPE',
  'QKV_PROJECTION',
  'Q_PROJECTION',
  'K_PROJECTION',
  'V_PROJECTION',
  'O_PROJECTION',
  'ATTENTION',
  'KV_CACHE',
  'LINEAR',
  'MLP',
  'ACTIVATION',
  'SAMPLING',
  'MEMORY',
  'SYNCHRONIZATION',
  'OTHER',
  'UNKNOWN',
];

export function categoryStyle(category: string | null | undefined): CategoryStyle {
  if (category && CATEGORY_STYLES[category]) return CATEGORY_STYLES[category];
  return CATEGORY_STYLES.UNKNOWN;
}

export function stageColor(stage: string): string {
  switch (stage) {
    case 'DECODE':
      return '#38bdf8';
    case 'EXTEND':
      return '#f59e0b';
    case 'PREFILL':
      return '#f59e0b';
    case 'MIXED':
      return '#a78bfa';
    case 'IDLE':
      return '#6b7280';
    default:
      return '#9ca3af';
  }
}
