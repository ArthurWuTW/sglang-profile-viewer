import { useMemo, useState } from 'react';
import type { StepSummary } from '../models/types';
import { formatDuration } from '../utils/format';
import { stageColor } from '../utils/colors';

const STAGE_ORDER = ['PREFILL', 'EXTEND', 'DECODE', 'MIXED', 'IDLE', 'UNKNOWN'];

interface Props {
  steps: StepSummary[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function StepList({ steps, loading, selectedId, onSelect, onToggleCollapse, collapsed }: Props) {
  const [stageFilter, setStageFilter] = useState<string>('ALL');

  const stages = useMemo(() => {
    const present = new Set(steps.map((s) => s.stage));
    return STAGE_ORDER.filter((s) => present.has(s));
  }, [steps]);

  const grouped = useMemo(() => {
    const filtered = stageFilter === 'ALL' ? steps : steps.filter((s) => s.stage === stageFilter);
    const map = new Map<string, StepSummary[]>();
    for (const s of filtered) {
      const list = map.get(s.stage) ?? [];
      list.push(s);
      map.set(s.stage, list);
    }
    return STAGE_ORDER.filter((st) => map.has(st)).map((st) => ({ stage: st, items: map.get(st)! }));
  }, [steps, stageFilter]);

  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        className="flex flex-col items-center pt-2 gap-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 transition-colors h-full"
        title="Expand steps panel"
      >
        <span className="text-xs">▶</span>
        <span className="text-[10px] tracking-wider" style={{ writingMode: 'vertical-rl' }}>
          STEPS ({steps.length})
        </span>
      </button>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-gray-800 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          Steps ({steps.length})
        </span>
        <div className="flex items-center gap-1">
          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded text-xs px-1.5 py-0.5 text-gray-300"
          >
            <option value="ALL">All stages</option>
            {stages.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button
            onClick={onToggleCollapse}
            className="text-gray-500 hover:text-gray-200 text-xs px-1"
            title="Collapse"
          >
            ◀
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading && <div className="p-3 text-sm text-gray-500">Loading steps…</div>}
        {!loading && steps.length === 0 && (
          <div className="p-3 text-sm text-gray-500">No steps detected.</div>
        )}
        {grouped.map(({ stage, items }) => (
          <div key={stage}>
            <div
              className="px-3 pt-2 pb-1 text-[11px] font-bold tracking-wider sticky top-0 bg-gray-950/95 backdrop-blur"
              style={{ color: stageColor(stage) }}
            >
              {stage} <span className="text-gray-600 font-normal">({items.length})</span>
            </div>
            {items.map((s) => (
              <button
                key={s.id}
                onClick={() => onSelect(s.id)}
                className={`w-full text-left px-3 py-1.5 flex items-center justify-between gap-2 hover:bg-gray-800/60 transition-colors border-l-2 ${
                  selectedId === s.id
                    ? 'bg-gray-800 border-l-sky-500'
                    : 'border-l-transparent'
                }`}
                title={s.rawName}
              >
                <span className="text-sm text-gray-200">
                  #{s.index}
                  {s.batchSize != null && (
                    <span className="ml-1.5 text-[11px] text-gray-500">BS={s.batchSize}</span>
                  )}
                  {s.tokens != null && (
                    <span className="ml-1.5 text-[11px] text-gray-500">toks={s.tokens}</span>
                  )}
                </span>
                <span className="text-xs text-gray-400 tabular-nums">{formatDuration(s.durationUs)}</span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
