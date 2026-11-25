import { describe, expect, it } from "vitest";
import { balanceAt, frameAt } from "./replay";
import type { Moment, TimelineItem } from "@/types/api";

const t = (id: string, ts: string, edge: string): TimelineItem => ({
  transaction_id: id, timestamp: ts, source: "a", target: "b", amount: 10, edge_id: edge,
});
const timeline = [t("1", "2026-11-09T09:00", "x->m"), t("2", "2026-11-09T14:00", "m->h"), t("3", "2026-11-11T15:00", "h->k")];
const moments: Moment[] = [
  { timestamp: "2026-11-09T09:00", label: "first", kind: "first_in" },
  { timestamp: "2026-11-11T15:00", label: "cash out", kind: "cash_out" },
];

describe("frameAt", () => {
  it("shows nothing before the first step", () => {
    const f = frameAt(timeline, moments, -1);
    expect(f.visibleEdges.size).toBe(0);
    expect(f.current).toBeNull();
  });
  it("reveals edges in time order and reports moments once", () => {
    expect(frameAt(timeline, moments, 0).newMoments.map((m) => m.kind)).toEqual(["first_in"]);
    expect(frameAt(timeline, moments, 1).newMoments).toEqual([]);
    const last = frameAt(timeline, moments, 2);
    expect([...last.visibleEdges]).toEqual(["x->m", "m->h", "h->k"]);
    expect(last.newMoments.map((m) => m.kind)).toEqual(["cash_out"]);
  });
});

describe("balanceAt", () => {
  const pts = [
    { timestamp: "2026-11-09T00:00", balance: 0 },
    { timestamp: "2026-11-09T10:00", balance: 900 },
    { timestamp: "2026-11-09T14:00", balance: 40 },
  ];
  it("takes the last point at or before now", () => {
    expect(balanceAt(pts, "2026-11-09T12:00")).toBe(900);
    expect(balanceAt(pts, "2026-11-10T00:00")).toBe(40);
    expect(balanceAt(pts, null)).toBe(0);
    expect(balanceAt(undefined, "x")).toBeNull();
  });
});
