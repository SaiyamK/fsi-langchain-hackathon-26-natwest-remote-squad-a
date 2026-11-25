import { ArrowUpRight, ExternalLink } from "lucide-react";
import { Link } from "react-router";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet } from "@/components/ui/dialog";
import { MemoryCard } from "@/features/memory/MemoryCard";
import { api } from "@/lib/api";
import { confidence, dateTime, money, patternLabel, paymentFormat } from "@/lib/format";
import { TX_STATUS } from "@/lib/status";
import { selectClock, useLive } from "@/stores/live";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-2 py-1 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

/** Transaction detail (LS-9): all fields, status, the agent's reason, and a link to the case. */
export function TxDetailSheet({ id }: { id: string }) {
  const row = useLive((s) => s.txById[id]);
  const clock = useLive(selectClock);
  if (!row) return null;
  return (
    <Sheet title={`${row.transaction_id} · ${money(row.amount, row.currency)}`} description={`${row.customer_name} · ${dateTime(row.timestamp)}`}>
      <div className="mb-3 flex items-center gap-2">
        <StatusBadge meta={TX_STATUS[row.status]} />
        {row.case_id && (
          <Button asChild size="sm" variant="default" className="ml-auto">
            <Link to={`/cases/${encodeURIComponent(row.case_id)}`}>
              <ArrowUpRight /> Open case
            </Link>
          </Button>
        )}
      </div>
      {row.reason && (
        <p className="mb-3 rounded-md bg-surface-2 px-3 py-2 text-sm">
          <span className="font-semibold">Agent reason: </span>
          {row.reason}
        </p>
      )}
      <div className="mb-3 space-y-2">
        {row.memory.map((m) => (
          <MemoryCard key={`${m.kind}-${m.key}`} card={m} asOf={clock} />
        ))}
      </div>
      <dl className="divide-y divide-border">
        <Field label="Sender">{row.sender.name} <span className="font-mono text-xs text-muted">{row.sender.account}</span></Field>
        <Field label="Receiver">{row.receiver.name} <span className="font-mono text-xs text-muted">{row.receiver.account}</span></Field>
        <Field label="Payment format">{paymentFormat(row.txn_type)}</Field>
        <Field label="Country">{row.country ?? "—"}{row.branch && ` · branch ${row.branch}`}</Field>
        <Field label="Rule score">{row.rule_score} (rules-only would {row.baseline})</Field>
        <Field label="Rule reasons">{row.rule_reasons.length ? row.rule_reasons.join("; ") : "none"}</Field>
        {row.pattern && <Field label="Pattern">{patternLabel(row.pattern)}</Field>}
        {row.decided_by && <Field label="Decided by">{row.decided_by}{row.final_decision && ` · ${row.final_decision}`}</Field>}
        {row.confidence !== null && <Field label="Confidence">{confidence(row.confidence)}</Field>}
        {row.trace_run_id && (
          <Field label="Trace">
            <a className="inline-flex items-center gap-1 text-accent hover:underline" href={api.traceUrl(row.trace_run_id)} target="_blank" rel="noreferrer">
              Open in LangSmith <ExternalLink className="size-3" />
            </a>
          </Field>
        )}
      </dl>
    </Sheet>
  );
}
