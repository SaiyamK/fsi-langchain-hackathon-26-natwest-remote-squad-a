import { Filter, Radio, Search } from "lucide-react";
import { useState } from "react";
import { Card, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Empty } from "@/components/ui/empty";
import { ActivityPanel } from "@/features/agents/ActivityPanel";
import { cn } from "@/lib/cn";
import { useLive } from "@/stores/live";
import { usePrefs } from "@/stores/prefs";
import { StreamControls } from "./StreamControls";
import { StreamRow } from "./StreamRow";
import { TxDetailSheet } from "./TxDetailSheet";
import { useRelatedHighlight } from "./useRelatedHighlight";
import { useStreamRows, type StreamFilter } from "./useStreamRows";

export function StreamPage() {
  const [filter, setFilter] = useState<StreamFilter>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const rows = useStreamRows(filter, query);
  const cases = useLive((s) => s.cases);
  const latestSeq = useLive((s) => s.txOrder.length);
  const reduced = usePrefs((s) => s.reducedMotion);
  const related = useRelatedHighlight();

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-3 p-3 lg:grid-cols-[1fr_22rem]">
      <Card className="flex min-h-0 flex-col">
        <CardHeader title="Live Stream" icon={<Radio />} />
        <div className="space-y-2 border-b border-border px-3 py-2">
          <StreamControls />
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-md border border-border p-0.5" role="group" aria-label="Filter">
              {(["all", "flags"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  aria-pressed={filter === f}
                  className={cn("rounded px-2 py-0.5 text-xs", filter === f ? "bg-surface-2 font-medium" : "text-muted")}
                >
                  {f === "all" ? "All" : <><Filter className="mr-1 inline size-3" />Flagged & needs analyst</>}
                </button>
              ))}
            </div>
            <label className="relative">
              <Search className="pointer-events-none absolute top-1.5 left-2 size-3.5 text-muted" aria-hidden />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Customer or account"
                aria-label="Filter by customer or account"
                className="h-7 w-52 rounded-md border border-border bg-surface pr-2 pl-7 text-xs focus:border-accent focus:outline-none"
              />
            </label>
            <span className="ml-auto text-[11px] text-muted">Newest first · showing up to 250</span>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          {rows.length === 0 ? (
            <Empty icon={<Radio />} title={latestSeq ? "Nothing matches the filter" : "Press Start to stream transactions"}>
              {!latestSeq && "Transactions arrive in time order. Most are cleared by rules; the agents investigate the rest."}
            </Empty>
          ) : (
            <table className="w-full border-collapse">
              <thead className="sticky top-0 z-10 bg-surface text-left text-[11px] tracking-wide text-muted uppercase">
                <tr className="border-b border-border">
                  <th className="w-1 p-0" />
                  <th className="px-2 py-1.5 font-medium">Time</th>
                  <th className="px-2 py-1.5 font-medium">Sender</th>
                  <th className="px-2 py-1.5 font-medium">Receiver</th>
                  <th className="px-2 py-1.5 text-right font-medium">Amount</th>
                  <th className="hidden px-2 py-1.5 font-medium lg:table-cell">Format</th>
                  <th className="px-2 py-1.5 font-medium">Status</th>
                  <th className="px-2 py-1.5 font-medium">Case</th>
                </tr>
              </thead>
              <tbody aria-live="polite" aria-relevant="additions">
                {rows.map((r, i) => (
                  <StreamRow
                    key={r.transaction_id}
                    row={r}
                    isNetwork={Boolean(r.case_id && cases[r.case_id]?.kind === "network")}
                    related={related.has(r.transaction_id)}
                    fresh={i < 20}
                    reduced={reduced}
                    onSelect={setSelected}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
      <ActivityPanel />
      <Dialog open={selected !== null} onOpenChange={(o) => !o && setSelected(null)}>
        {selected && <TxDetailSheet id={selected} />}
      </Dialog>
    </div>
  );
}
