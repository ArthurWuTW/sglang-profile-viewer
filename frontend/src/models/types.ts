export type ProfileStatus =
  | 'discovered'
  | 'parsing'
  | 'ready'
  | 'failed'
  | 'failed_temporary'
  | 'removed';

export interface ProfileSummary {
  id: string;
  path: string;
  fileName: string;
  sizeBytes: number;
  status: ProfileStatus;
  error: string | null;
  createdAt: number | null;
  runTimestamp: number | null;
  eventCount: number;
  stepCount: number;
  traceStartUs: number | null;
  traceEndUs: number | null;
  stageSummary?: Record<string, number>;
  compatibility?: string;
}

export interface StepSummary {
  id: string;
  index: number;
  stage: string;
  batchSize: number | null;
  tokens: number | null;
  startUs: number;
  durationUs: number;
  endUs: number;
  eventCount: number;
  rawName: string;
}

export interface TopKernel {
  name: string;
  count: number;
  totalUs: number;
}

export interface StepMetrics {
  wallDurationUs: number;
  gpuBusyUs: number;
  gpuKernelCount: number;
  unknownCount: number;
  semanticDurationByCategory: Record<string, number>;
  topKernels: TopKernel[];
}

export interface TimelineEvent {
  id: string;
  name: string;
  rawName: string;
  category: string;
  confidence: string | null;
  framework: string | null;
  kind: string;
  ts: number;
  dur: number | null;
  pid: number | null;
  tid: number | null;
}

export interface StepDetail {
  step: StepSummary;
  metrics: StepMetrics;
  contextEvents: TimelineEvent[];
  events: TimelineEvent[];
  totalEventCount: number;
  truncated: boolean;
}

export interface EventSourceMapping {
  repository?: string;
  path?: string;
  symbol?: string;
  description?: string;
  ruleId?: string;
  framework?: string;
}

export interface EventDetail {
  id: string;
  raw: Record<string, unknown>;
  normalized: Record<string, unknown>;
  semantic: {
    category: string | null;
    name: string | null;
    confidence: string | null;
    framework: string | null;
    ruleId: string | null;
  };
  source: EventSourceMapping | null;
  step: StepSummary | null;
  flows: TimelineEvent[];
}

export interface MonitorStatus {
  monitoring: boolean;
  profileRoot: string;
  lastScan: number | null;
  profileCount: number;
  readyCount: number;
}

export type WsMessage =
  | { type: 'init'; monitor: MonitorStatus; profiles: ProfileSummary[] }
  | { type: 'profile_discovered'; profileId: string; profile: ProfileSummary }
  | { type: 'profile_parsing'; profileId: string }
  | { type: 'profile_ready'; profileId: string; profile: ProfileSummary }
  | { type: 'profile_failed'; profileId: string; error: string; temporary: boolean }
  | { type: 'profile_removed'; profileId: string }
  | { type: 'monitor_status'; monitor: MonitorStatus };
