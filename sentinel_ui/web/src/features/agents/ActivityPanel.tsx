import { Bot, CheckCircle2, CircleDashed, ExternalLink, Loader2 } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Card, CardHeader } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import { MemoryCard } from "@/features/memory/MemoryCard";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { confidence, money } from "@/lib/format";
import { selectClock, useLive } from "@/stores/live";
import { usePrefs } from "@/stores/prefs";
import type { Activity, Step } from "@/types/api";

const ROUTE_LABEL = { auto_cleared: "auto-cleared", escalated: "escalated", sent_to_analyst: "sent to analyst" } as const;

function StepRow({ step }: { step: Step }) {
  const reduced = usePrefs((s) => s.reducedMotion);
  const Icon = step.state === "done" ? CheckCircle2 : step.state === "working" ? Loader2 : CircleDashed;
  return (
    <motion.li layout={!reduced} initial={reduced ? false : { opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className="flex gap-2">
      <Icon
        className={cn("mt-0.5 size-4 shrink-0", step.state === "done" ? "text-cleared" : step.state === "working" ? "animate-spin text-review" : "text-rules")}
        aria-label={step.state}
      />
      <div className="min-w-0 text-sm">
        <div className="flex items-baseline gap-2">
          <span className="font-medium">{step.label}</span>
          <span className="text-[11px] text-muted">{step.state}</span>
        </div>
        {step.finding && <p className="text-xs text-muted">{step.finding}</p>}
        {step.tools.length > 0 && (
          <p className="truncate font-mono text-[10px] text-muted/80" title={step.tools.join(", ")}>
            {step.tools.join(" · ")}
          </p>
        )}
      </div>
    </motion.li>
  );
}

/** The investigation as a row of steps (EX-1). Used live on the stream and as the record in the case view. */
export function Investigation({ activity, asOf }: { activity: Activity; asOf?: string | null }) {
  return (
    <div className="space-y-2">
      <ol className="space-y-2" aria-label={`Investigation of ${activity.transaction_id}`}>
        {activity.steps.map((s) => (
          <StepRow key={s.key} step={s} />
        ))}
      </ol>
      {activity.memory.map((m) => (
        <MemoryCard key={`${m.kind}-${m.key}`} card={m} asOf={asOf} compact />
      ))}
      {activity.route && (
        <div className="rounded-md bg-surface-2 px-2 py-1.5 text-xs">
          <span className="font-semibold">{activity.verdict ?? "—"}</span>, confidence {confidence(activity.confidence)} →{" "}
          <span className="font-semibold">{ROUTE_LABEL[activity.route]}</span>
          {activity.route_reason && <p className="mt-0.5 text-muted">{activity.route_reason}</p>}
        </div>
      )}
      <div className="flex items-center gap-2 text-[11px] text-muted">
        {activity.replayed && <span className="rounded bg-memory-soft px-1 text-memory">replayed</span>}
        {activity.seconds !== null && activity.done && <span>{activity.seconds}s</span>}
        {activity.trace_run_id && (
          <a className="inline-flex items-center gap-0.5 text-accent hover:underline" href={api.traceUrl(activity.trace_run_id)} target="_blank" rel="noreferrer">
            LangSmith trace <ExternalLink className="size-3" />
          </a>
        )}
      </div>
    </div>
  );
}

/** Live panel: the most recent investigation, with a switcher for others running at once (EX-1.4). */
export function ActivityPanel() {
  const order = useLive((s) => s.activityOrder);
  const activity = useLive((s) => s.activity);
  const clock = useLive(selectClock);
  const [picked, setPicked] = useState<string | null>(null);
  const running = order.filter((id) => activity[id] && !activity[id]!.done);
  const currentId = picked && activity[picked] ? picked : (running[0] ?? order[0]);
  const current = currentId ? activity[currentId] : undefined;

  return (
    <Card className="flex min-h-0 flex-col">
      <CardHeader title="Agent activity" icon={<Bot />} action={running.length > 1 && <span className="text-xs text-review">{running.length} running</span>} />
      {order.length > 1 && (
        <div className="flex gap-1 overflow-x-auto border-b border-border px-2 py-1.5" role="tablist" aria-label="Investigations">
          {order.slice(0, 12).map((id) => {
            const a = activity[id];
            if (!a) return null;
            return (
              <button
                key={id}
                role="tab"
                aria-selected={id === currentId}
                onClick={() => setPicked(id)}
                className={cn(
                  "shrink-0 rounded-md border px-2 py-0.5 text-[11px] whitespace-nowrap",
                  id === currentId ? "border-accent text-text" : "border-border text-muted",
                )}
              >
                {!a.done && <Loader2 className="mr-1 inline size-3 animate-spin text-review" />}
                {a.customer_name.split(" ")[0]} · {id.replace("TX-", "")}
              </button>
            );
          })}
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <AnimatePresence mode="wait">
          {current ? (
            <motion.div key={current.transaction_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <p className="mb-2 text-sm">
                <span className="font-semibold">{current.customer_name}</span> · {money(current.amount)} ·{" "}
                <span className="font-mono text-xs text-muted">{current.transaction_id}</span>
              </p>
              <Investigation activity={current} asOf={clock} />
            </motion.div>
          ) : (
            <Empty icon={<Bot />} title="No investigations yet">
              The agents start when the rules tier flags a transaction.
            </Empty>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
}
