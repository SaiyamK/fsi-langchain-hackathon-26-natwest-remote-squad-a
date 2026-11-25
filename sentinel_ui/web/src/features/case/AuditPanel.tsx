import { dateTime } from "@/lib/format";
import type { CaseDetail } from "@/types/api";

/** Analyst actions, status changes and every use of the cross-customer graph tool (FR-10). */
export function AuditPanel({ detail }: { detail: CaseDetail }) {
  return (
    <div className="space-y-3 text-xs">
      <section>
        <h3 className="mb-1 font-semibold text-muted uppercase">Cross-customer graph tool ({detail.network_audit.length})</h3>
        {detail.network_audit.length ? (
          <ul className="space-y-1">
            {detail.network_audit.map((a, i) => (
              <li key={i} className="rounded bg-surface-2 px-2 py-1">
                {dateTime(a.as_of)} · {a.caller} traced from <span className="font-mono">{a.seed_account}</span> → {a.accounts_returned.length} accounts returned (graph summary only, no profiles)
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">Not used for this case.</p>
        )}
      </section>
      <section>
        <h3 className="mb-1 font-semibold text-muted uppercase">Case history</h3>
        {detail.audit.length ? (
          <ol className="space-y-1">
            {detail.audit.map((a, i) => (
              <li key={i}><span className="text-muted">{dateTime(a.at)}</span> · {a.kind.replace(/_/g, " ")}: {a.detail}</li>
            ))}
          </ol>
        ) : (
          <p className="text-muted">No actions yet.</p>
        )}
      </section>
    </div>
  );
}
