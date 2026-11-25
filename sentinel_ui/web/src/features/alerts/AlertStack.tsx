import { ArrowUpRight, UserRoundSearch, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Link } from "react-router";
import { Button } from "@/components/ui/button";
import { money, patternLabel } from "@/lib/format";
import { useLive } from "@/stores/live";
import { usePrefs } from "@/stores/prefs";
import type { Alert } from "@/types/api";
import { DecisionForm } from "./DecisionForm";

function AlertCard({ alert, onDismiss }: { alert: Alert; onDismiss: () => void }) {
  const [deciding, setDeciding] = useState(false);
  return (
    <div className="rounded-lg border border-review bg-surface p-3 shadow-xl" role="alertdialog" aria-labelledby={`alert-${alert.transaction_id}`}>
      <div className="flex items-start gap-2">
        <UserRoundSearch className="mt-0.5 size-5 shrink-0 text-review" aria-hidden />
        <div className="min-w-0 flex-1">
          <p id={`alert-${alert.transaction_id}`} className="text-sm font-semibold">
            Needs your decision · {alert.customer_name}
          </p>
          <p className="text-sm">
            {money(alert.amount, alert.currency)} · {patternLabel(alert.pattern)} ·{" "}
            <span className="font-mono text-xs text-muted">{alert.transaction_id}</span>
          </p>
          <p className="mt-1 text-sm">{alert.question}</p>
          <p className="text-xs text-review">{alert.leaning}</p>
          {alert.main_reason && <p className="mt-0.5 text-xs text-muted">Unsure because: {alert.main_reason}</p>}
          {alert.hard_flags.length > 0 && <p className="mt-0.5 text-xs text-flagged">Hard flag: {alert.hard_flags[0]}</p>}
        </div>
        <button onClick={onDismiss} className="rounded p-1 text-muted hover:bg-surface-2" aria-label="Dismiss (stays in Flagged Transactions)">
          <X className="size-4" />
        </button>
      </div>
      <div className="mt-2">
        {deciding ? (
          <DecisionForm transactionId={alert.transaction_id} compact />
        ) : (
          <div className="flex gap-2">
            {alert.case_id && (
              <Button asChild size="sm">
                <Link to={`/cases/${encodeURIComponent(alert.case_id)}`}>
                  <ArrowUpRight /> Open case
                </Link>
              </Button>
            )}
            <Button size="sm" variant="clear" onClick={() => setDeciding(true)}>Clear</Button>
            <Button size="sm" variant="escalate" onClick={() => setDeciding(true)}>Escalate</Button>
          </div>
        )}
      </div>
    </div>
  );
}

/** Alerts slide in on any screen, newest on top, and stay until acted on or dismissed (EX-4). */
export function AlertStack() {
  const alerts = useLive((s) => s.alerts);
  const reduced = usePrefs((s) => s.reducedMotion);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const visible = alerts.filter((a) => !dismissed.has(a.transaction_id)).slice(0, 3);

  return (
    <div className="pointer-events-none fixed right-4 bottom-10 z-30 flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="assertive">
      <AnimatePresence initial={false}>
        {visible.map((a) => (
          <motion.div
            key={a.transaction_id}
            layout={!reduced}
            initial={reduced ? false : { opacity: 0, x: 60 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, x: 60 }}
            className="pointer-events-auto"
          >
            <AlertCard alert={a} onDismiss={() => setDismissed((d) => new Set(d).add(a.transaction_id))} />
          </motion.div>
        ))}
      </AnimatePresence>
      {alerts.length - dismissed.size > 3 && (
        <p className="pointer-events-auto self-end rounded bg-surface px-2 py-0.5 text-xs text-muted shadow">
          +{alerts.length - dismissed.size - 3} more in Flagged
        </p>
      )}
    </div>
  );
}
