import type { BalancePoint, Moment, TimelineItem } from "@/types/api";

/** What the graph shows at replay step `cursor` (−1 = before the first transfer, length−1 = everything). */
export interface ReplayFrame {
  now: string | null;
  visibleEdges: Set<string>;
  current: TimelineItem | null;
  /** Moments reached by this step that weren't reached by the previous one. */
  newMoments: Moment[];
}

export function frameAt(timeline: TimelineItem[], moments: Moment[], cursor: number): ReplayFrame {
  const clamped = Math.min(cursor, timeline.length - 1);
  const visibleEdges = new Set<string>();
  for (let i = 0; i <= clamped; i++) visibleEdges.add(timeline[i]!.edge_id);
  const current = clamped >= 0 ? timeline[clamped]! : null;
  const now = current?.timestamp ?? null;
  const prev = clamped > 0 ? timeline[clamped - 1]!.timestamp : "";
  const newMoments = now ? moments.filter((m) => m.timestamp > prev && m.timestamp <= now) : [];
  return { now, visibleEdges, current, newMoments };
}

/** The account's balance (net flow) at `now`: the last point at or before it. */
export function balanceAt(points: BalancePoint[] | undefined, now: string | null): number | null {
  if (!points?.length) return null;
  if (!now) return 0;
  let value = 0;
  for (const p of points) {
    if (p.timestamp > now) break;
    value = p.balance;
  }
  return value;
}

export function peakBalance(points: BalancePoint[] | undefined): number {
  return Math.max(1, ...(points ?? []).map((p) => p.balance));
}
