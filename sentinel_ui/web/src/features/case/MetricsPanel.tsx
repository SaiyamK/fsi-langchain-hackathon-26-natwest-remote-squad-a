import { CheckCircle2, CircleSlash, Flag, HelpCircle } from "lucide-react";
import { motion } from "motion/react";
import { Card, CardHeader } from "@/components/ui/card";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/cn";
import { usePrefs } from "@/stores/prefs";
import type { CaseDetail, RedFlag } from "@/types/api";

const STATE = {
  fired: { icon: Flag, label: "Fired", cls: "text-flagged" },
  not_fired: { icon: CheckCircle2, label: "Not fired", cls: "text-cleared" },
  no_data: { icon: CircleSlash, label: "No data", cls: "text-rules" },
} as const;

function FlagRow({ flag, index }: { flag: RedFlag; index: number }) {
  const reduced = usePrefs((s) => s.reducedMotion);
  const s = STATE[flag.state];
  return (
    <motion.li
      initial={reduced ? false : { opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: reduced ? 0 : 0.08 * index }}
      className={cn("py-1.5", !flag.applicable && "opacity-50")}
    >
      <div className="flex items-start gap-2 text-sm">
        <s.icon className={cn("mt-0.5 size-4 shrink-0", s.cls)} aria-hidden />
        <div className="min-w-0">
          <p className={cn(flag.state === "fired" && "font-medium")}>
            {flag.label} <span className={cn("text-xs", s.cls)}>· {s.label}</span>
          </p>
          <p className="text-xs text-muted">{flag.evidence}</p>
          {!flag.applicable && <p className="text-[10px] text-muted">Not typical for this pattern</p>}
        </div>
      </div>
    </motion.li>
  );
}

/** Pattern metrics and the red-flag checklist (FR-5). Thresholds in use are listed (FR-5.3). */
export function MetricsPanel({ detail }: { detail: CaseDetail }) {
  const flags = [...detail.red_flags].sort((a, b) => Number(b.applicable) - Number(a.applicable));
  return (
    <Card className="flex min-h-0 flex-col">
      <CardHeader
        title="Metrics & red flags"
        action={
          <Tooltip content={<ul>{Object.entries(detail.thresholds).map(([k, v]) => <li key={k}><strong>{k}:</strong> {v}</li>)}</ul>}>
            <button className="inline-flex items-center gap-1 text-xs text-muted"><HelpCircle className="size-3.5" />Thresholds</button>
          </Tooltip>
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <dl className="grid grid-cols-2 gap-px bg-border">
          {detail.metrics.map((m) => (
            <div key={m.label} className="bg-surface px-3 py-2" title={m.hint ?? undefined}>
              <dt className="text-[11px] text-muted">{m.label}</dt>
              <dd className="font-semibold tabular-nums">{m.value}</dd>
              {m.hint && <dd className="truncate text-[10px] text-muted">{m.hint}</dd>}
            </div>
          ))}
        </dl>
        <ul className="divide-y divide-border px-3" aria-label="Red flags">
          {flags.map((f, i) => (
            <FlagRow key={f.key} flag={f} index={i} />
          ))}
        </ul>
      </div>
    </Card>
  );
}
