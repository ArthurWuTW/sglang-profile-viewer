import type { EventDetail } from '../models/types';
import { categoryStyle } from '../utils/colors';
import { formatDuration } from '../utils/format';

interface Props {
  detail: EventDetail | null;
  loading: boolean;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-xs py-1 border-b border-gray-800/60">
      <span className="w-32 shrink-0 text-gray-500">{label}</span>
      <span className="text-gray-200 break-all min-w-0">{children}</span>
    </div>
  );
}

export default function EventDetail({ detail, loading }: Props) {
  if (loading) {
    return <div className="p-4 text-sm text-gray-500">Loading event…</div>;
  }
  if (!detail) {
    return <div className="p-4 text-sm text-gray-500">Click an event in the timeline to inspect it.</div>;
  }
  const style = categoryStyle(detail.semantic.category);
  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="flex items-center gap-2 mb-2">
        <span
          className="text-xs font-bold px-2 py-0.5 rounded"
          style={{ color: style.color, background: `${style.color}22` }}
        >
          {style.displayName}
        </span>
        <span className="text-sm font-semibold">
          {detail.semantic.name ?? String(detail.raw.name ?? '')}
        </span>
        {detail.semantic.confidence && (
          <span className="text-[10px] text-gray-500 uppercase">confidence: {detail.semantic.confidence}</span>
        )}
      </div>

      <Row label="Duration">{formatDuration((detail.raw.dur as number) ?? null)}</Row>
      <Row label="Start (rel)">{formatDuration((detail.normalized.ts as number) ?? null)}</Row>
      <Row label="Start (abs)">{(detail.raw.ts as number)?.toFixed(1)} µs</Row>
      <Row label="Kind">{String(detail.raw.cat ?? '—')}</Row>
      <Row label="PID / TID">
        {String(detail.raw.pid ?? '—')} / {String(detail.raw.tid ?? '—')}
      </Row>
      <Row label="Parent step">
        {detail.step ? `${detail.step.stage} Step #${detail.step.index}` : '—'}
      </Row>
      <Row label="Backend">{detail.semantic.framework ?? '—'}</Row>
      <Row label="Mapping rule">{detail.semantic.ruleId ?? '—'}</Row>

      {detail.source && (
        <div className="mt-2">
          <div className="text-xs text-gray-500 mb-1">Source mapping</div>
          <div className="text-xs bg-gray-900 border border-gray-800 rounded p-2 space-y-0.5">
            {detail.source.repository && <div>repo: <span className="text-gray-300">{detail.source.repository}</span></div>}
            {detail.source.path && (
              <div className="font-mono text-[11px] text-sky-300 break-all">{detail.source.path}</div>
            )}
            {detail.source.symbol && <div>symbol: <span className="text-gray-300">{detail.source.symbol}</span></div>}
            {detail.source.description && <div className="text-gray-400">{detail.source.description}</div>}
          </div>
        </div>
      )}

      {detail.flows.length > 0 && (
        <div className="mt-2">
          <div className="text-xs text-gray-500 mb-1">Related flow events</div>
          <div className="space-y-0.5">
            {detail.flows.map((f) => (
              <div key={f.id} className="text-[11px] font-mono text-gray-400 truncate">
                {f.kind} · {f.rawName}
              </div>
            ))}
          </div>
        </div>
      )}

      <details className="mt-2">
        <summary className="text-xs text-gray-500 cursor-pointer">Raw event JSON</summary>
        <pre className="mt-1 text-[11px] font-mono bg-gray-900 border border-gray-800 rounded p-2 overflow-x-auto text-gray-300">
          {JSON.stringify(detail.raw, null, 2)}
        </pre>
      </details>
    </div>
  );
}
