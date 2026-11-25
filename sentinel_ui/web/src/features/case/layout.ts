import type { Role } from "@/types/api";

export interface Point {
  x: number;
  y: number;
}

export interface LayoutInput {
  nodes: { id: string; role: Role }[];
  edges: { source: string; target: string }[];
  layout: "chain" | "fan_in" | "fan_out";
  width: number;
  height: number;
  pad?: number;
}

const CHAIN_COLUMNS: Partial<Record<Role, number>> = { source: 0, mule: 1, subject: 1, hub: 2, sink: 3, other: 3 };

function spread(count: number, from: number, to: number): number[] {
  if (count <= 1) return [(from + to) / 2];
  return Array.from({ length: count }, (_, i) => from + ((to - from) * i) / (count - 1));
}

/**
 * Deterministic positions per pattern (FR-4.5):
 * - chain (mule ring): left → right columns, source → mule → hub → cash-out; sources sorted by the mule they feed;
 * - fan_in: the hub in the middle, senders on an arc to its left (arrows inward), recipients to its right;
 * - fan_out: the hub in the middle, recipients on a wide arc to its right (arrows outward), senders to its left.
 */
export function computeLayout({ nodes, edges, layout, width, height, pad = 48 }: LayoutInput): Record<string, Point> {
  const pos: Record<string, Point> = {};
  if (!nodes.length) return pos;

  if (layout === "chain") {
    const columns: string[][] = [[], [], [], []];
    for (const n of nodes) columns[CHAIN_COLUMNS[n.role] ?? 3]!.push(n.id);
    const muleIndex = new Map(columns[1]!.map((id, i) => [id, i]));
    const feeds = (id: string) => {
      const target = edges.find((e) => e.source === id && muleIndex.has(e.target))?.target;
      return target ? (muleIndex.get(target) ?? 99) : 99;
    };
    columns[0]!.sort((a, b) => feeds(a) - feeds(b) || a.localeCompare(b));
    const xs = spread(4, pad + 100, width - pad - 70); // room for source labels on the left
    columns.forEach((col, c) => {
      spread(col.length, pad, height - pad).forEach((y, i) => (pos[col[i]!] = { x: xs[c]!, y }));
    });
    return pos;
  }

  const hub = nodes.find((n) => n.role === "hub" || n.role === "subject") ?? nodes[0]!;
  const cx = width / 2;
  const cy = height / 2;
  pos[hub.id] = { x: cx, y: cy };
  const isIn = (id: string) => edges.some((e) => e.source === id && e.target === hub.id);
  const others = nodes.filter((n) => n.id !== hub.id);
  const ins = others.filter((n) => isIn(n.id)).map((n) => n.id).sort();
  const outs = others.filter((n) => !isIn(n.id)).map((n) => n.id).sort();
  const rx = width / 2 - pad - 30;
  const ry = height / 2 - pad;

  const arc = (ids: string[], fromDeg: number, toDeg: number) => {
    spread(ids.length, fromDeg, toDeg).forEach((deg, i) => {
      const rad = (deg * Math.PI) / 180;
      pos[ids[i]!] = { x: cx + rx * Math.cos(rad), y: cy + ry * Math.sin(rad) };
    });
  };
  const wideOut = layout === "fan_out";
  arc(ins, wideOut ? 150 : 110, wideOut ? 210 : 250); // left side
  arc(outs, wideOut ? -70 : -40, wideOut ? 70 : 40); // right side
  return pos;
}
