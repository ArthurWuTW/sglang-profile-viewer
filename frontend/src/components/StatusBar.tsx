import type { MonitorStatus } from '../models/types';
import { formatClock } from '../utils/format';

interface Props {
  monitor: MonitorStatus | null;
  wsConnected: boolean;
  autoFollow: boolean;
  onAutoFollowChange: (v: boolean) => void;
}

export default function StatusBar({ monitor, wsConnected, autoFollow, onAutoFollowChange }: Props) {
  const monitoring = wsConnected && (monitor?.monitoring ?? false);
  return (
    <div className="flex items-center gap-4 px-4 py-1.5 text-xs text-gray-400 border-b border-gray-800 bg-gray-900/60">
      <span className="flex items-center gap-1.5">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            monitoring ? 'bg-green-500 animate-pulse' : 'bg-red-500'
          }`}
        />
        {monitoring ? 'Monitoring' : 'Not monitoring'}
      </span>
      <span className="hidden md:inline" title={monitor?.profileRoot}>
        Dir: <span className="text-gray-300 truncate max-w-[220px] inline-block align-bottom">{monitor?.profileRoot ?? '—'}</span>
      </span>
      <span>Last scan: {formatClock(monitor?.lastScan ?? null)}</span>
      <span>
        Profiles: <span className="text-gray-300">{monitor?.profileCount ?? 0}</span>
        <span className="text-gray-600"> ({monitor?.readyCount ?? 0} ready)</span>
      </span>
      <span className="ml-auto flex items-center gap-2">
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={autoFollow}
            onChange={(e) => onAutoFollowChange(e.target.checked)}
            className="accent-sky-500"
          />
          Auto-follow new profiles
        </label>
        <span className={wsConnected ? 'text-green-500' : 'text-red-400'}>
          {wsConnected ? 'WS connected' : 'WS disconnected'}
        </span>
      </span>
    </div>
  );
}
