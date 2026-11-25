import { Flag, Network, Search, UserRoundSearch, Users } from "lucide-react";
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { StatusBadge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import { NetworkThumbnail } from "@/features/case/NetworkThumbnail";
import { cn } from "@/lib/cn";
import { confidence, money, patternLabel, shortDate } from "@/lib/format";
import { CASE_STATUS } from "@/lib/status";
import { sortCases } from "@/stores/reducer";
import { useLive } from "@/stores/live";
import { usePrefs } from "@/stores/prefs";
import type { CaseSummary } from "@/types/api";

type Quick = "all" | "mine" | "network";

function matches(c: CaseSummary, quick: Quick, pattern: string, q: string) {
  if (quick === "mine" && c.status !== "awaiting_analyst") return false;
  if (quick === "network" && c.kind !== "network") return false;
  if (pattern && c.pattern !== pattern) return false;
  const s = q.trim().toLowerCase();
  return !s || c.case_id.toLowerCase().includes(s) || c.lead_name.toLowerCase().includes(s) || c.lead_account.toLowerCase().includes(s);
}

function CaseItem({ c, isNew }: { c: CaseSummary; isNew: boolean }) {
  const reduced = usePrefs((s) => s.reducedMotion);
  const meta = CASE_STATUS[c.status];
  return (
    <motion.li layout={!reduced} initial={reduced ? false : { opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}>
      <Link
        to={`/cases/${encodeURIComponent(c.case_id)}`}
        className={cn(
          "flex gap-3 rounded-lg border border-border bg-surface p-3 hover:border-accent focus-visible:border-accent",
          c.status === "awaiting_analyst" && "border-l-4 border-l-review",
          c.status === "new" && "border-l-4 border-l-flagged",
        )}
      >
        <NetworkThumbnail summary={c} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{patternLabel(c.pattern)}</span>
            {c.kind === "network" && <Network className="size-4 text-muted" aria-label="Network case" />}
            <span className="truncate">{c.lead_name}</span>
            <span className="font-mono text-[11px] text-muted">{c.case_id}</span>
            {isNew && <span className="rounded bg-accent px-1.5 text-[10px] font-bold text-white">NEW</span>}
            <span className="ml-auto"><StatusBadge meta={meta} /></span>
          </div>
          <p className="mt-0.5 line-clamp-2 text-sm text-muted">{c.why}</p>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted tabular-nums">
            <span><Users className="mr-1 inline size-3" />{c.accounts} account{c.accounts === 1 ? "" : "s"}</span>
            <span>{c.transaction_ids.length} flagged · {c.related_transaction_ids.length} transfers</span>
            <span>{money(c.total_amount)}</span>
            <span>{shortDate(c.first_ts)} → {shortDate(c.last_ts)}</span>
            <span>verdict <strong className={c.verdict === "escalate" ? "text-flagged" : "text-cleared"}>{c.verdict ?? "—"}</strong>, confidence {confidence(c.confidence)}</span>
            <span>severity {c.severity}</span>
          </div>
        </div>
      </Link>
    </motion.li>
  );
}

/** The analyst's work queue (FQ-1..FQ-9). Updates live; new items are marked until opened. */
export function QueuePage() {
  const cases = useLive((s) => s.cases);
  const opened = usePrefs((s) => s.openedCases);
  const [params, setParams] = useSearchParams();
  const quick = (params.get("view") as Quick) || "all";
  const pattern = params.get("pattern") ?? "";
  const [q, setQ] = useState(params.get("q") ?? "");

  const all = useMemo(() => sortCases(Object.values(cases)), [cases]);
  const list = all.filter((c) => matches(c, quick, pattern, q));
  const patterns = [...new Set(all.map((c) => c.pattern))];
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  return (
    <div className="h-full overflow-y-auto p-3">
      <Card>
        <CardHeader title="Flagged Transactions" icon={<Flag />} action={<span className="text-xs text-muted">{all.length} cases</span>} />
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
          {([
            ["all", "All", Flag],
            ["mine", "Needs my decision", UserRoundSearch],
            ["network", "Network cases", Network],
          ] as const).map(([key, label, Icon]) => (
            <button
              key={key}
              onClick={() => set("view", key === "all" ? "" : key)}
              aria-pressed={quick === key}
              className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs", quick === key ? "border-accent bg-surface-2 font-medium" : "border-border text-muted")}
            >
              <Icon className="size-3.5" /> {label}
            </button>
          ))}
          <select
            value={pattern}
            onChange={(e) => set("pattern", e.target.value)}
            aria-label="Pattern"
            className="h-7 rounded-md border border-border bg-surface px-1.5 text-xs"
          >
            <option value="">All patterns</option>
            {patterns.map((p) => (
              <option key={p} value={p}>{patternLabel(p)}</option>
            ))}
          </select>
          <label className="relative ml-auto">
            <Search className="pointer-events-none absolute top-1.5 left-2 size-3.5 text-muted" aria-hidden />
            <input
              value={q}
              onChange={(e) => { setQ(e.target.value); set("q", e.target.value); }}
              placeholder="Account, customer or case ID"
              aria-label="Search cases"
              className="h-7 w-60 rounded-md border border-border bg-surface pr-2 pl-7 text-xs focus:border-accent focus:outline-none"
            />
          </label>
        </div>
        {list.length ? (
          <ul className="space-y-2 p-3">
            {list.map((c) => (
              <CaseItem key={c.case_id} c={c} isNew={(opened[c.case_id] ?? -1) < c.updated_seq && (c.status === "new" || c.status === "awaiting_analyst")} />
            ))}
          </ul>
        ) : (
          <Empty icon={<Flag />} title={all.length ? "No cases match" : "No flagged transactions yet"}>
            {!all.length && "Cases appear here as soon as the agents flag a transaction or ask for a decision."}
          </Empty>
        )}
      </Card>
    </div>
  );
}
