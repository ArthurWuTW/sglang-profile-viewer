import type { ProfileSummary } from '../models/types';
import { formatBytes, formatTimestamp } from '../utils/format';

const STATUS_STYLES: Record<string, string> = {
  ready: 'bg-green-500/20 text-green-400 border-green-500/40',
  parsing: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  discovered: 'bg-blue-500/20 text-blue-400 border-blue-500/40',
  failed: 'bg-red-500/20 text-red-400 border-red-500/40',
  failed_temporary: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
  removed: 'bg-gray-500/20 text-gray-400 border-gray-500/40',
};

interface Props {
  profiles: ProfileSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function ProfileList({ profiles, selectedId, onSelect, collapsed, onToggleCollapse }: Props) {
  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        className="flex flex-col items-center pt-2 gap-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 transition-colors h-full"
        title="Expand profiles panel"
      >
        <span className="text-xs">▶</span>
        <span className="text-[10px] tracking-wider" style={{ writingMode: 'vertical-rl' }}>
          PROFILES ({profiles.length})
        </span>
      </button>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-gray-800 text-xs font-semibold uppercase tracking-wider text-gray-400 flex items-center justify-between">
        <span>Profiles ({profiles.length})</span>
        <button
          onClick={onToggleCollapse}
          className="text-gray-500 hover:text-gray-200 text-xs px-1"
          title="Collapse"
        >
          ◀
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {profiles.length === 0 && (
          <div className="p-3 text-sm text-gray-500">
            No profiles discovered yet.
            <br />
            Waiting for <code className="text-gray-400">*.json.gz</code> files…
          </div>
        )}
        {profiles.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`w-full text-left px-3 py-2 border-b border-gray-800/60 hover:bg-gray-800/60 transition-colors ${
              selectedId === p.id ? 'bg-gray-800 border-l-2 border-l-sky-500' : 'border-l-2 border-l-transparent'
            }`}
            title={p.path}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium truncate">{p.fileName}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded border uppercase shrink-0 ${
                  STATUS_STYLES[p.status] ?? STATUS_STYLES.removed
                }`}
              >
                {p.status.replace('_', ' ')}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-2 text-[11px] text-gray-500">
              <span>{formatBytes(p.sizeBytes)}</span>
              <span>·</span>
              <span>{p.stepCount} steps</span>
              <span>·</span>
              <span>{formatTimestamp(p.runTimestamp ?? p.createdAt)}</span>
            </div>
            {p.error && <div className="mt-1 text-[11px] text-red-400 truncate">{p.error}</div>}
          </button>
        ))}
      </div>
    </div>
  );
}
