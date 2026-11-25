import { useQuery } from "@tanstack/react-query";
import { Sheet } from "@/components/ui/dialog";
import { MemoryCard } from "@/features/memory/MemoryCard";
import { api } from "@/lib/api";
import { dateTime, money, paymentFormat } from "@/lib/format";
import { ROLE_META } from "@/lib/status";
import type { GraphNode } from "@/types/api";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[10rem_1fr] gap-2 py-1 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

/** The selected account: KYC, screening, money in/out, role, red flags and precedents (FR-7). */
export function AccountSheet({ node, asOf }: { node: GraphNode; asOf: string }) {
  const { data } = useQuery({ queryKey: ["account", node.id, asOf], queryFn: () => api.account(node.id) });
  return (
    <Sheet title={node.label} description={`${node.id} · ${ROLE_META[node.role]?.label ?? node.role} in this case`}>
      {!data ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : (
        <div className="space-y-4">
          {data.hard_flags.length > 0 && (
            <div className="rounded-md border border-flagged bg-flagged-soft px-3 py-2 text-sm text-flagged">
              <strong>Hard red flag:</strong> {data.hard_flags.join("; ")}
            </div>
          )}
          <dl className="divide-y divide-border">
            <Row label="Bank">{data.bank}</Row>
            {!data.external && (
              <>
                <Row label="Customer">{data.customer_type} · {data.occupation}</Row>
                <Row label="Account opened">{dateTime(data.account_opened)} ({data.account_age_days} days)</Row>
                <Row label="KYC risk rating">{data.risk_rating}</Row>
                <Row label="PEP / sanctions">{data.pep ? "PEP" : "Not PEP"}{data.screening.length ? ` · ${data.screening.join("; ")}` : " · no screening hits"}</Row>
                <Row label="Expected a month">{money(data.expected_monthly_credits ?? 0)} credits · {money(data.expected_monthly_cash ?? 0)} cash</Row>
              </>
            )}
            <Row label="Last 30 days">{money(data.money_in)} in · {money(data.money_out)} out · {data.counterparties} counterparties</Row>
          </dl>
          {node.flags.length > 0 && (
            <section>
              <h3 className="mb-1 text-xs font-semibold text-muted uppercase">Red flags for this account</h3>
              <ul className="list-disc pl-5 text-sm">{node.flags.map((f) => <li key={f}>{f}</li>)}</ul>
            </section>
          )}
          <section className="space-y-2">
            <h3 className="text-xs font-semibold text-muted uppercase">Precedents</h3>
            {data.precedents.length ? data.precedents.map((p) => <MemoryCard key={p.key} card={p} asOf={asOf} />) : <p className="text-sm text-muted">None</p>}
          </section>
          <section>
            <h3 className="mb-1 text-xs font-semibold text-muted uppercase">Transactions (last 30 days, excluding card spend)</h3>
            <ul className="divide-y divide-border text-xs">
              {data.transactions.map((t) => (
                <li key={t.transaction_id} className="grid grid-cols-[7rem_1fr_5rem] gap-2 py-1">
                  <span className="text-muted">{dateTime(t.timestamp)}</span>
                  <span>{paymentFormat(t.txn_type)} <span className="font-mono text-muted">{t.transaction_id}</span></span>
                  <span className="text-right tabular-nums">{money(t.amount)}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </Sheet>
  );
}
