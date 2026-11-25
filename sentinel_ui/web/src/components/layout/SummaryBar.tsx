import { ArrowRight, Info } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/cn";
import { count, percent } from "@/lib/format";
import { TONE_CLASSES, type Tone } from "@/lib/status";
import { useLive } from "@/stores/live";
import { usePrefs } from "@/stores/prefs";

function Stat({ label, value, tone, basis }: { label: string; value: ReactNode; tone?: Tone; basis?: string }) {
  const reduced = usePrefs((s) => s.reducedMotion);
  const body = (
    <div className="min-w-0 px-3 py-1.5">
      <div className="flex items-center gap-1 text-[11px] whitespace-nowrap text-muted">
        {tone && <span className={cn("size-1.5 rounded-full", TONE_CLASSES[tone].dot)} aria-hidden />}
        {label}
        {basis && <Info className="size-3 opacity-60" aria-hidden />}
      </div>
      <motion.div
        key={String(value)}
        initial={reduced ? false : { opacity: 0.4, y: -3 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-base font-semibold tabular-nums"
      >
        {value}
      </motion.div>
    </div>
  );
  return basis ? (
    <Tooltip content={basis}>
      <div tabIndex={0} className="cursor-help rounded-md focus-visible:outline-2">{body}</div>
    </Tooltip>
  ) : (
    body
  );
}

/** Live counters (LS-6) and the value ticker (EX-3). Every figure is computed by the server from this session. */
export function SummaryBar() {
  const c = useLive((s) => s.counters);
  if (!c) return <div className="h-14 border-b border-border bg-surface" />;
  return (
    <div className="flex flex-wrap items-stretch divide-x divide-border border-b border-border bg-surface">
      <Stat label="Received" value={`${count(c.received)} / ${count(c.total)}`} />
      <Stat label="Cleared by rules" value={percent(c.cleared_rules, c.received)} tone="rules"
        basis={`${count(c.cleared_rules)} of ${count(c.received)} cleared by the rules tier, with no model call`} />
      <Stat label="Under review" value={c.under_review} tone="review" />
      <Stat label="Flagged" value={c.flagged} tone="flagged" />
      <Stat label="Needs analyst" value={c.needs_analyst} tone="review" />
      <Stat label="Agent model calls" value={count(c.model_calls)}
        basis={`${count(c.investigations)} investigations so far, ${count(c.tokens)} tokens`} />

      <Link
        to="/results"
        className="ml-auto flex items-stretch divide-x divide-border bg-surface-2/60 hover:bg-surface-2"
        aria-label="Value so far: open the Results view"
      >
        <Stat label="Alerts: rules-only → Sentinel" value={<>{c.rules_alerts} → <span className="text-cleared">{c.sentinel_alerts}</span></>}
          basis="Rules-only: transactions the rules tier alone would escalate. Sentinel: transactions an analyst had to look at (flagged, or sent for a decision)." />
        <Stat label="False positives avoided" value={c.false_positives_avoided}
          basis="Rules-only would have escalated these; the synthetic labels say clear; Sentinel cleared them without an analyst. Labels are used only for this figure." />
        <Stat label="Analyst hours saved" value={`${c.analyst_hours_saved}`}
          basis={`Alerts avoided × ${c.minutes_per_alert} minutes per alert (an assumption, configurable). Transactions still under review aren't counted.`} />
        <Stat label="Tokens: Sentinel vs all-to-agents" value={c.investigations ? `${compact(c.tokens)} vs ${compact(c.tokens_if_all_to_agents)}` : "—"}
          basis={`Tokens used so far vs the estimate if every one of the ${count(c.total)} transactions went to the agents (${count(Math.round(c.avg_tokens_per_investigation))} tokens per investigation on average). Tokens, not money: no published price for the gateway model (DEC-005).`} />
        <span className="flex items-center px-2 text-muted"><ArrowRight className="size-4" aria-hidden /></span>
      </Link>
    </div>
  );
}

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1000)}k`;
  return String(n);
}
