import { describe, expect, it } from "vitest";
import type { CaseSummary, Snapshot, TxRow } from "@/types/api";
import { applyEvent, fromSnapshot, sortCases } from "./reducer";

const tx = (id: string, status: TxRow["status"] = "cleared_rules"): TxRow => ({
  transaction_id: id, user_id: "U", account_id: "A", customer_name: "C", timestamp: "2026-10-01T06:00",
  direction: "in", txn_type: "bacs", amount: 1, currency: "GBP", country: "GB", branch: null,
  sender: { account: null, name: "x" }, receiver: { account: "A", name: "C" }, rule_score: 0, rule_reasons: [],
  baseline: "clear", status, pattern: null, case_id: null, reason: null, decided_by: "rules", final_decision: "clear",
  confidence: null, memory: [], sar_id: null, trace_run_id: null, replayed: false, seq: 1,
});

const snap: Snapshot = {
  session: { mode: "offline", state: "idle", clock: null, speed: 8, replay: null, live_transactions: [], agents_available: false, model: null },
  transactions: [tx("T1")], cases: [], counters: null as never, alerts: [], activity: [],
};

describe("live reducer", () => {
  it("appends new transactions and updates known ones in place", () => {
    let s = fromSnapshot(snap);
    s = applyEvent(s, { type: "tx", data: tx("T2", "under_review") });
    s = applyEvent(s, { type: "tx", data: tx("T2", "flagged") });
    expect(s.txOrder).toEqual(["T1", "T2"]);
    expect(s.txById.T2!.status).toBe("flagged");
  });

  it("stacks alerts newest first and removes them", () => {
    let s = fromSnapshot(snap);
    const alert = (id: string) => ({ transaction_id: id, case_id: null, customer_name: "", amount: 1, currency: "GBP", pattern: "", question: "", leaning: "", main_reason: "", why_review: [], hard_flags: [] });
    s = applyEvent(s, { type: "alert", data: alert("A") });
    s = applyEvent(s, { type: "alert", data: alert("B") });
    expect(s.alerts.map((a) => a.transaction_id)).toEqual(["B", "A"]);
    s = applyEvent(s, { type: "alert_removed", data: { transaction_id: "B" } });
    expect(s.alerts.map((a) => a.transaction_id)).toEqual(["A"]);
  });

  it("clears everything on reset", () => {
    const s = applyEvent(fromSnapshot(snap), { type: "reset", data: snap.session });
    expect(s.txOrder).toEqual([]);
    expect(s.epoch).toBe(1);
  });
});

describe("sortCases", () => {
  const c = (id: string, status: CaseSummary["status"], severity: number, last: string) =>
    ({ case_id: id, status, severity, last_ts: last }) as CaseSummary;
  it("puts needs-analyst first, then severity, then newest", () => {
    const order = sortCases([c("a", "new", 90, "2"), c("b", "awaiting_analyst", 10, "1"), c("c", "new", 90, "3"), c("d", "cleared", 99, "9")]);
    expect(order.map((x) => x.case_id)).toEqual(["b", "c", "a", "d"]);
  });
});
