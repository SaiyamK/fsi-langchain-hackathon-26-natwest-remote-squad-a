import { describe, expect, it } from "vitest";
import { computeLayout } from "./layout";

describe("computeLayout", () => {
  it("lays a mule ring out left to right by role", () => {
    const pos = computeLayout({
      layout: "chain",
      width: 800,
      height: 400,
      nodes: [
        { id: "s1", role: "source" },
        { id: "m1", role: "mule" },
        { id: "h", role: "hub" },
        { id: "k", role: "sink" },
      ],
      edges: [
        { source: "s1", target: "m1" },
        { source: "m1", target: "h" },
        { source: "h", target: "k" },
      ],
    });
    expect(pos.s1!.x).toBeLessThan(pos.m1!.x);
    expect(pos.m1!.x).toBeLessThan(pos.h!.x);
    expect(pos.h!.x).toBeLessThan(pos.k!.x);
  });

  it("puts the hub in the middle of a fan-in with senders on the left", () => {
    const pos = computeLayout({
      layout: "fan_in",
      width: 600,
      height: 400,
      nodes: [
        { id: "hub", role: "subject" },
        { id: "a", role: "source" },
        { id: "b", role: "source" },
        { id: "z", role: "sink" },
      ],
      edges: [
        { source: "a", target: "hub" },
        { source: "b", target: "hub" },
        { source: "hub", target: "z" },
      ],
    });
    expect(pos.hub).toEqual({ x: 300, y: 200 });
    expect(pos.a!.x).toBeLessThan(300);
    expect(pos.b!.x).toBeLessThan(300);
    expect(pos.z!.x).toBeGreaterThan(300);
  });

  it("is deterministic", () => {
    const input = {
      layout: "fan_out" as const,
      width: 500,
      height: 300,
      nodes: [
        { id: "h", role: "hub" as const },
        { id: "r1", role: "sink" as const },
        { id: "r2", role: "sink" as const },
      ],
      edges: [
        { source: "h", target: "r1" },
        { source: "h", target: "r2" },
      ],
    };
    expect(computeLayout(input)).toEqual(computeLayout(input));
  });
});
