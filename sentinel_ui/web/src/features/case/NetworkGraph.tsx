import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { compactMoney } from "@/lib/format";
import type { CaseDetail, GraphEdge, GraphNode } from "@/types/api";
import { computeLayout, type Point } from "./layout";
import { balanceAt, peakBalance, type ReplayFrame } from "./replay";
import { ROLE_FILL } from "./roles";

const W = 960;
const H = 480;
const RADIUS: Record<string, number> = { hub: 24, subject: 24, mule: 17, source: 9, sink: 14, other: 10 };

export type Selection = { kind: "node"; id: string } | { kind: "edge"; id: string } | null;

interface Props {
  detail: CaseDetail;
  frame: ReplayFrame;
  replaying: boolean;
  selection: Selection;
  onSelect: (s: Selection) => void;
  edgeLabels: boolean;
  reduced: boolean;
}

function shorten(a: Point, b: Point, ra: number, rb: number) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  return { x1: a.x + (dx / len) * ra, y1: a.y + (dy / len) * ra, x2: b.x - (dx / len) * (rb + 4), y2: b.y - (dy / len) * (rb + 4) };
}

/** The case network: directed, sized by amount, styled by role, animated during replay (FR-4, EX-5). */
export function NetworkGraph({ detail, frame, replaying, selection, onSelect, edgeLabels, reduced }: Props) {
  const [hover, setHover] = useState<Selection>(null);
  const pos = useMemo(
    () => computeLayout({ nodes: detail.nodes, edges: detail.edges, layout: detail.summary.layout, width: W, height: H }),
    [detail.nodes, detail.edges, detail.summary.layout],
  );
  const nodeById = useMemo(() => Object.fromEntries(detail.nodes.map((n) => [n.id, n])), [detail.nodes]);
  const maxAmount = Math.max(1, ...detail.edges.map((e) => e.amount));
  const focus = hover ?? selection;
  const lit = useMemo(() => {
    if (!focus) return null;
    const ids = new Set<string>();
    if (focus.kind === "node") {
      ids.add(focus.id);
      for (const e of detail.edges) if (e.source === focus.id || e.target === focus.id) ids.add(e.id).add(e.source).add(e.target);
    } else {
      const e = detail.edges.find((x) => x.id === focus.id);
      if (e) ids.add(e.id).add(e.source).add(e.target);
    }
    return ids;
  }, [focus, detail.edges]);
  const dim = (id: string) => (lit && !lit.has(id) ? 0.12 : 1);
  const radius = (n: GraphNode) => RADIUS[n.role] ?? 10;

  const edgeEl = (e: GraphEdge) => {
    const a = pos[e.source];
    const b = pos[e.target];
    const na = nodeById[e.source];
    const nb = nodeById[e.target];
    if (!a || !b || !na || !nb) return null;
    const shown = !replaying || frame.visibleEdges.has(e.id);
    const { x1, y1, x2, y2 } = shorten(a, b, radius(na), radius(nb));
    const width = 1.2 + 7 * Math.sqrt(e.amount / maxAmount);
    const selected = selection?.kind === "edge" && selection.id === e.id;
    return (
      <g
        key={e.id}
        opacity={shown ? dim(e.id) : 0.07}
        onMouseEnter={() => setHover({ kind: "edge", id: e.id })}
        onMouseLeave={() => setHover(null)}
        onClick={() => onSelect({ kind: "edge", id: e.id })}
        className="cursor-pointer"
        style={{ transition: reduced ? undefined : "opacity 300ms" }}
      >
        <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="transparent" strokeWidth={Math.max(width, 12)} />
        <line
          x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={selected ? "var(--accent)" : "var(--muted)"}
          strokeOpacity={selected ? 1 : 0.55}
          strokeWidth={width}
          markerEnd={selected ? "url(#arrow-accent)" : "url(#arrow)"}
        />
        {edgeLabels && shown && (e.amount / maxAmount > 0.12 || detail.edges.length < 14) && (
          <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 5} textAnchor="middle" className="fill-muted text-[10px]" paintOrder="stroke" stroke="var(--surface)" strokeWidth={3}>
            {compactMoney(e.amount)}{e.count > 1 ? ` ×${e.count}` : ""}
          </text>
        )}
      </g>
    );
  };

  const moving = frame.current && replaying ? frame.current : null;
  const from = moving ? pos[moving.source] : undefined;
  const to = moving ? pos[moving.target] : undefined;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full select-none" role="img" aria-label={detail.finding}>
      <defs>
        {(["arrow", "arrow-accent"] as const).map((id) => (
          <marker key={id} id={id} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill={id === "arrow" ? "var(--muted)" : "var(--accent)"} />
          </marker>
        ))}
      </defs>
      <rect width={W} height={H} fill="transparent" onClick={() => onSelect(null)} />
      {detail.edges.map(edgeEl)}

      {moving && from && to && (
        <motion.g
          key={`${moving.transaction_id}`}
          initial={{ x: from.x, y: from.y, opacity: 0 }}
          animate={{ x: to.x, y: to.y, opacity: [0, 1, 1, 0] }}
          transition={{ duration: reduced ? 0 : 0.65, ease: "easeInOut" }}
        >
          <circle r={6} fill="var(--accent)" />
          <text y={-10} textAnchor="middle" className="fill-accent text-[11px] font-semibold" paintOrder="stroke" stroke="var(--surface)" strokeWidth={3}>
            {compactMoney(moving.amount)}
          </text>
        </motion.g>
      )}

      {detail.nodes.map((n) => {
        const p = pos[n.id];
        if (!p) return null;
        const r = radius(n);
        const points = detail.balances[n.id];
        const level = replaying && points ? Math.max(0, (balanceAt(points, frame.now) ?? 0) / peakBalance(points)) : null;
        const hard = n.hard_flags.length > 0;
        const sideLabel = n.role === "source" && detail.summary.layout === "chain";
        return (
          <g
            key={n.id}
            transform={`translate(${p.x},${p.y})`}
            opacity={dim(n.id)}
            onMouseEnter={() => setHover({ kind: "node", id: n.id })}
            onMouseLeave={() => setHover(null)}
            onClick={() => onSelect({ kind: "node", id: n.id })}
            onKeyDown={(ev) => (ev.key === "Enter" || ev.key === " ") && onSelect({ kind: "node", id: n.id })}
            tabIndex={0}
            role="button"
            aria-label={`${n.label}, ${n.role}${hard ? ", hard red flag" : ""}`}
            className="cursor-pointer focus:outline-none"
            style={{ transition: reduced ? undefined : "opacity 300ms" }}
          >
            {hard && <circle r={r + 6} fill="none" stroke="var(--flagged)" strokeWidth={2.5} strokeDasharray="4 2" />}
            <circle r={r} fill="var(--surface)" stroke={ROLE_FILL[n.role]} strokeWidth={2} strokeDasharray={n.external ? "3 2" : undefined} />
            {level === null ? (
              <circle r={r - 3} fill={ROLE_FILL[n.role]} opacity={0.85} />
            ) : (
              <motion.circle animate={{ r: Math.max(1.5, (r - 3) * Math.sqrt(Math.min(level, 1))) }} transition={{ duration: reduced ? 0 : 0.4 }} fill={ROLE_FILL[n.role]} opacity={0.85} />
            )}
            {n.flags.length > 0 && (
              <g transform={`translate(${r * 0.7},${-r - 2})`} aria-hidden>
                <path d="M0 0 v10 M0 0 h8 l-2 3 l2 3 h-8" fill="var(--flagged)" stroke="var(--flagged)" strokeWidth={1.2} />
              </g>
            )}
            <text
              x={sideLabel ? -r - 5 : 0}
              y={sideLabel ? 3 : r + 13}
              textAnchor={sideLabel ? "end" : "middle"}
              className={n.role === "source" ? "fill-muted text-[9px]" : "fill-text text-[11px] font-medium"}
              paintOrder="stroke"
              stroke="var(--surface)"
              strokeWidth={3}
            >
              {n.label.length > 22 ? `${n.label.slice(0, 21)}…` : n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
