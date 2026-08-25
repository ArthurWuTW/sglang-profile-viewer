import { useEffect, useMemo, useRef, useState } from 'react';
import { scaleLinear } from 'd3-scale';
import { select } from 'd3-selection';
import { zoom, zoomIdentity, ZoomBehavior, ZoomTransform } from 'd3-zoom';
import type { StepDetail, TimelineEvent } from '../models/types';
import { categoryStyle, stageColor } from '../utils/colors';
import { formatDuration } from '../utils/format';

const ROW_H = 26;
const LABEL_W = 150;
const AXIS_H = 24;
const MIN_BAR = 1.5;

interface Props {
  detail: StepDetail;
  selectedEventId: string | null;
  onSelectEvent: (id: string) => void;
  hiddenCategories: Set<string>;
  search: string;
}

interface Row {
  category: string;
  events: TimelineEvent[];
}

export default function Timeline({ detail, selectedEventId, onSelectEvent, hiddenCategories, search }: Props) {
  const { step, events } = detail;
  const svgRef = useRef<SVGSVGElement>(null);
  const [width, setWidth] = useState(800);
  const [transform, setTransform] = useState<ZoomTransform>(zoomIdentity);
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  // Measure container width
  useEffect(() => {
    const el = svgRef.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setWidth(Math.max(300, e.contentRect.width));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Filter events
  const visibleEvents = useMemo(() => {
    const q = search.trim().toLowerCase();
    return events.filter((e) => {
      if (hiddenCategories.has(e.category)) return false;
      if (q && !e.name.toLowerCase().includes(q) && !e.rawName.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [events, hiddenCategories, search]);

  // Time domain: step window extended to cover all visible GPU work
  const domainEnd = useMemo(() => {
    let end = step.durationUs;
    for (const e of visibleEvents) {
      const endT = e.ts + (e.dur ?? 0);
      if (endT > end) end = endT;
    }
    return Math.max(end, 1);
  }, [visibleEvents, step.durationUs]);

  // Group into rows by category (fixed order)
  const rows: Row[] = useMemo(() => {
    const byCat = new Map<string, TimelineEvent[]>();
    for (const e of visibleEvents) {
      const cat = e.category || 'UNKNOWN';
      const list = byCat.get(cat) ?? [];
      list.push(e);
      byCat.set(cat, list);
    }
    const order = Object.keys(categoryStyle);
    const sorted = [...byCat.keys()].sort((a, b) => {
      const ia = order.indexOf(a);
      const ib = order.indexOf(b);
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });
    return sorted.map((cat) => ({ category: cat, events: byCat.get(cat)! }));
  }, [visibleEvents]);

  const height = AXIS_H + rows.length * ROW_H + 8;

  const baseScale = useMemo(
    () => scaleLinear().domain([0, domainEnd]).range([0, width - LABEL_W - 16]),
    [domainEnd, width],
  );
  const x = useMemo(() => {
    const s = baseScale.copy().domain([
      (-transform.x) / transform.k,
      (width - LABEL_W - 16 - transform.x) / transform.k,
    ]);
    return s;
  }, [baseScale, transform, width]);

  // d3-zoom for pan/zoom
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const sel = select(svg);
    const z = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 200])
      .translateExtent([[0, 0], [width, height]])
      .extent([[0, 0], [width, height]])
      .on('zoom', (event) => {
        setTransform(event.transform);
      });
    sel.call(z);
    zoomRef.current = z;
    return () => {
      sel.on('.zoom', null);
    };
  }, [width, height]);

  const resetZoom = () => {
    if (svgRef.current && zoomRef.current) {
      select(svgRef.current).call(zoomRef.current.transform, zoomIdentity);
    }
  };

  // Ticks
  const ticks = useMemo(() => {
    const t = x.ticks(Math.max(4, Math.floor((width - LABEL_W) / 120)));
    return t;
  }, [x, width]);

  const stepEndX = x(step.durationUs);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800 bg-gray-900/40">
        <span
          className="text-sm font-bold px-2 py-0.5 rounded"
          style={{ color: stageColor(step.stage), background: `${stageColor(step.stage)}22` }}
        >
          {step.stage}
        </span>
        <span className="text-sm font-semibold">Step #{step.index}</span>
        {step.batchSize != null && <span className="text-xs text-gray-400">BS={step.batchSize}</span>}
        {step.tokens != null && <span className="text-xs text-gray-400">toks={step.tokens}</span>}
        <span className="text-xs text-gray-400 tabular-nums">{formatDuration(step.durationUs)}</span>
        <span className="text-[11px] text-gray-500">
          {detail.metrics.gpuKernelCount} kernels · GPU busy {formatDuration(detail.metrics.gpuBusyUs)}
        </span>
        {detail.truncated && (
          <span className="text-[11px] text-orange-400">
            showing {events.length} of {detail.totalEventCount} events
          </span>
        )}
        <button
          onClick={resetZoom}
          className="ml-auto text-xs px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300"
        >
          Reset zoom
        </button>
      </div>

      {/* SVG timeline */}
      <div className="flex-1 overflow-auto min-h-0">
        <svg ref={svgRef} width={width} height={height} className="block select-none">
          {/* step window background */}
          <rect
            x={x(0)}
            y={0}
            width={Math.max(0, stepEndX - x(0))}
            height={height}
            fill="#1e293b"
            opacity={0.35}
          />
          <line x1={stepEndX} x2={stepEndX} y1={0} y2={height} stroke="#475569" strokeDasharray="4 3" />

          {/* axis */}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={x(t)} x2={x(t)} y1={AXIS_H} y2={height} stroke="#1f2937" strokeWidth={1} />
              <text x={x(t) + 3} y={14} fill="#6b7280" fontSize={10}>
                {formatDuration(t)}
              </text>
            </g>
          ))}

          {/* rows */}
          {rows.map((row, ri) => {
            const style = categoryStyle(row.category);
            const y = AXIS_H + ri * ROW_H;
            return (
              <g key={row.category}>
                <text x={4} y={y + ROW_H / 2 + 4} fill={style.color} fontSize={11} fontWeight={600}>
                  {style.displayName}
                </text>
                <text x={LABEL_W - 6} y={y + ROW_H / 2 + 4} fill="#4b5563" fontSize={10} textAnchor="end">
                  {row.events.length}
                </text>
                {row.events.map((e) => {
                  const ex = x(e.ts);
                  const ew = Math.max(MIN_BAR, x(e.ts + (e.dur ?? 0)) - ex);
                  const isCpu = e.kind !== 'kernel' && e.kind !== 'gpu_memcpy' && e.kind !== 'gpu_memset';
                  const selected = e.id === selectedEventId;
                  return (
                    <rect
                      key={e.id}
                      x={ex}
                      y={y + 3}
                      width={ew}
                      height={ROW_H - 6}
                      rx={2}
                      fill={style.color}
                      fillOpacity={isCpu ? 0.35 : 0.9}
                      stroke={selected ? '#fff' : isCpu ? style.color : 'none'}
                      strokeWidth={selected ? 2 : 1}
                      className="cursor-pointer"
                      onClick={() => onSelectEvent(e.id)}
                    >
                      <title>
                        {`${e.name}\n${e.rawName}\n${formatDuration(e.dur)} @ ${formatDuration(e.ts)}`}
                      </title>
                    </rect>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
