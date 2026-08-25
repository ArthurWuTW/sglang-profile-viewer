export function formatDuration(us: number | null | undefined): string {
  if (us == null || Number.isNaN(us)) return '—';
  const abs = Math.abs(us);
  if (abs < 1000) return `${us.toFixed(1)} µs`;
  if (abs < 1_000_000) return `${(us / 1000).toFixed(2)} ms`;
  return `${(us / 1_000_000).toFixed(3)} s`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function formatTimestamp(ts: number | null | undefined): string {
  if (ts == null) return '—';
  // ts is unix seconds (float) from file mtime / run timestamp
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString();
}

export function formatClock(ts: number | null | undefined): string {
  if (ts == null) return '—';
  const d = new Date(ts * 1000);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString();
}

export function shortName(name: string, max = 48): string {
  if (!name) return '';
  // strip leading "void " and template args for compact display
  let n = name.replace(/^void\s+/, '');
  const lt = n.indexOf('<');
  if (lt > 0) n = n.slice(0, lt);
  if (n.length > max) n = n.slice(0, max - 1) + '…';
  return n;
}
