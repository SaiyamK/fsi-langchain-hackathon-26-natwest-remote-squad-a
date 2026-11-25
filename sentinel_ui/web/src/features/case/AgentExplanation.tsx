import { ExternalLink } from "lucide-react";
import { Investigation } from "@/features/agents/ActivityPanel";
import { MemoryCard } from "@/features/memory/MemoryCard";
import { api } from "@/lib/api";
import { confidence, patternLabel } from "@/lib/format";
import { useLive } from "@/stores/live";
import type { CaseDetail } from "@/types/api";

/** Verdict, explanation, investigation record, precedents and why it went to an analyst (FR-8, EX-1.3, EX-2). */
export function AgentExplanation({ detail }: { detail: CaseDetail }) {
  const rows = useLive((s) => s.txById);
  return (
    <div className="space-y-4">
      {detail.decisions.map((d) => {
        const row = rows[d.transaction_id];
        const activity = detail.activity.find((a) => a.transaction_id === d.transaction_id);
        const why = d.why_review ?? d.confidence_checks ?? [];
        return (
          <section key={d.transaction_id} className="space-y-2" aria-label={`Decision on ${d.transaction_id}`}>
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-mono text-xs text-muted">{d.transaction_id}</span>
              <span className={d.final_decision === "escalate" || d.agent_decision === "escalate" ? "font-semibold text-flagged" : "font-semibold text-cleared"}>
                {d.final_decision ?? `leaning ${d.agent_decision ?? "—"}`}
              </span>
              <span className="text-xs text-muted">
                {patternLabel(d.pattern)} · confidence {confidence(d.confidence)}
                {d.decided_by && ` · decided by ${d.decided_by}`}
              </span>
            </div>
            {d.reason && <p className="text-sm">{d.reason}</p>}
            {why.length > 0 && (
              <p className="rounded-md bg-review-soft px-2 py-1 text-xs text-review">
                Sent to an analyst because: {why.join("; ")}
              </p>
            )}
            {d.hard_flags?.length ? <p className="text-xs text-flagged">Hard flags: {d.hard_flags.join("; ")}</p> : null}
            {d.precedents_dropped?.length ? (
              <p className="text-xs text-muted">Cited but not applied: {d.precedents_dropped.map((p) => `${p.key} (${p.reason})`).join(", ")}</p>
            ) : null}
            {row?.memory.map((m) => <MemoryCard key={`${m.kind}-${m.key}`} card={m} asOf={detail.as_of} />)}
            {d.analyst_note && <p className="text-xs">Analyst note: “{d.analyst_note}”</p>}
            {activity && (
              <details className="rounded-md border border-border px-2 py-1.5" open={!activity.done}>
                <summary className="cursor-pointer text-xs font-medium">Investigation steps</summary>
                <div className="mt-2"><Investigation activity={activity} asOf={detail.as_of} /></div>
              </details>
            )}
            {!activity && d.trace_run_id && (
              <a className="inline-flex items-center gap-1 text-xs text-accent hover:underline" href={api.traceUrl(d.trace_run_id)} target="_blank" rel="noreferrer">
                LangSmith trace <ExternalLink className="size-3" />
              </a>
            )}
          </section>
        );
      })}
    </div>
  );
}
