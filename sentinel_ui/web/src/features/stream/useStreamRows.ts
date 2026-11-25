import { useMemo } from "react";
import { useLive } from "@/stores/live";
import type { TxRow } from "@/types/api";

export type StreamFilter = "all" | "flags";

const FLAG_STATUSES = new Set(["flagged", "needs_analyst"]);
const LIMIT = 250;

/** Newest first, filtered (LS-8), capped so the list stays fast. */
export function filterRows(rows: TxRow[], filter: StreamFilter, query: string): TxRow[] {
  const q = query.trim().toLowerCase();
  const out: TxRow[] = [];
  for (let i = rows.length - 1; i >= 0 && out.length < LIMIT; i--) {
    const r = rows[i]!;
    if (filter === "flags" && !FLAG_STATUSES.has(r.status)) continue;
    if (
      q &&
      !(
        r.customer_name.toLowerCase().includes(q) ||
        r.account_id.toLowerCase().includes(q) ||
        r.user_id.toLowerCase().includes(q) ||
        r.sender.name.toLowerCase().includes(q) ||
        r.receiver.name.toLowerCase().includes(q) ||
        (r.sender.account ?? "").toLowerCase().includes(q) ||
        (r.receiver.account ?? "").toLowerCase().includes(q)
      )
    )
      continue;
    out.push(r);
  }
  return out;
}

export function useStreamRows(filter: StreamFilter, query: string) {
  const txById = useLive((s) => s.txById);
  const txOrder = useLive((s) => s.txOrder);
  return useMemo(() => filterRows(txOrder.map((id) => txById[id]!), filter, query), [txById, txOrder, filter, query]);
}
