import { useMemo } from "react";
import type { CaseSummary } from "@/types/api";
import { computeLayout } from "./layout";
import { ROLE_FILL } from "./roles";

/** A small picture of the network shape, so the pattern is recognisable in the queue (FQ-4). */
export function NetworkThumbnail({ summary, width = 120, height = 64 }: { summary: CaseSummary; width?: number; height?: number }) {
  const pos = useMemo(
    () =>
      computeLayout({
        nodes: summary.shape_nodes,
        edges: summary.shape_edges.map(([source, target]) => ({ source, target })),
        layout: summary.layout,
        width,
        height,
        pad: 8,
      }),
    [summary, width, height],
  );
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${summary.layout.replace("_", "-")} network shape`} className="shrink-0 rounded bg-surface-2">
      {summary.shape_edges.map(([s, t]) => {
        const a = pos[s];
        const b = pos[t];
        return a && b ? <line key={`${s}-${t}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--muted)" strokeOpacity={0.5} strokeWidth={0.75} /> : null;
      })}
      {summary.shape_nodes.map((n) => {
        const p = pos[n.id];
        return p ? <circle key={n.id} cx={p.x} cy={p.y} r={n.role === "hub" || n.role === "subject" ? 4 : 2.5} fill={ROLE_FILL[n.role]} /> : null;
      })}
    </svg>
  );
}
