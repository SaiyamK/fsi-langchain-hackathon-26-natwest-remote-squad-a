import { useQuery } from "@tanstack/react-query";
import { BarChart3, ExternalLink } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/card";
import { Empty } from "@/components/ui/empty";
import { api } from "@/lib/api";
import { count, dateTime } from "@/lib/format";
import { useLive } from "@/stores/live";

/** Preferred metric order and labels (EX-13.1). Anything else in the file is shown after these. */
const METRICS: [string, string, boolean][] = [
  ["false_positive_rate", "False-positive rate", true],
  ["false_positives", "False positives", true],
  ["alert_precision", "Alert precision", false],
  ["recall_planted", "Recall on planted cases", false],
  ["decision_accuracy", "Decision accuracy", false],
  ["decision_accuracy_eval", "Decision accuracy", false],
  ["score_alignment_eval", "Score alignment", false],
  ["review_routing", "Review routing", false],
  ["review_routing_eval", "Review routing", false],
  ["human_review_rate", "Human review rate", true],
  ["reviews_month1", "Analyst reviews, month 1", true],
  ["reviews_month2", "Analyst reviews, month 2", true],
  ["override_correctness", "Correct precedent overrides", false],
  ["llm_share", "Transactions reaching an LLM", true],
  ["tokens_per_investigation", "Tokens per investigation", true],
];

function fmt(key: string, v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "string") return v;
  if (/rate|recall|accuracy|routing|share|correctness|precision|alignment/.test(key) && v <= 1) return `${(v * 100).toFixed(1)}%`;
  return Number.isInteger(v) ? count(v) : v.toFixed(2);
}

/** Rules-only vs Sentinel on the held-out set, loaded from the saved LangSmith experiments (EX-13). */
export function ResultsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["results"], queryFn: api.results });
  const counters = useLive((s) => s.counters);

  return (
    <div className="h-full space-y-3 overflow-y-auto p-3">
      <Card>
        <CardHeader title="Results: rules-only vs Sentinel" icon={<BarChart3 />} />
        {isLoading ? (
          <Empty title="Loading…" />
        ) : !data?.available || !data.data ? (
          <Empty icon={<BarChart3 />} title="No eval results yet">
            {data?.message} The view reads <code className="text-xs">{data?.path ?? "sentinel_aml_agent/results/eval_summary.json"}</code> and shows only real results.
          </Empty>
        ) : (
          <ResultsTable data={data.data} />
        )}
      </Card>
      {counters && (
        <Card>
          <CardHeader title="This session so far (live, not the eval)" />
          <dl className="grid grid-cols-2 gap-px bg-border text-sm md:grid-cols-4">
            {[
              ["Rules-only alerts", count(counters.rules_alerts)],
              ["Sentinel alerts", count(counters.sentinel_alerts)],
              ["False positives avoided", count(counters.false_positives_avoided)],
              ["Investigations", count(counters.investigations)],
            ].map(([k, v]) => (
              <div key={k} className="bg-surface px-3 py-2"><dt className="text-xs text-muted">{k}</dt><dd className="text-lg font-semibold tabular-nums">{v}</dd></div>
            ))}
          </dl>
        </Card>
      )}
    </div>
  );
}

function ResultsTable({ data }: { data: NonNullable<Awaited<ReturnType<typeof api.results>>["data"]> }) {
  const experiments = Object.entries(data.experiments ?? {});
  const keys = [
    ...METRICS.map(([k]) => k).filter((k) => experiments.some(([, e]) => e.metrics && k in e.metrics)),
    ...[...new Set(experiments.flatMap(([, e]) => Object.keys(e.metrics ?? {})))].filter((k) => !METRICS.some(([m]) => m === k)),
  ];
  const label = (k: string) => METRICS.find(([m]) => m === k)?.[1] ?? k.replace(/_/g, " ");
  return (
    <div className="space-y-3 p-3">
      {data.headline && <p className="text-lg font-semibold">{data.headline}</p>}
      <p className="text-xs text-muted">
        {data.dataset && <>Dataset {data.dataset} · </>}
        {data.n_transactions !== undefined && <>{count(data.n_transactions)} transactions · </>}
        {data.split && <>{data.split} split · </>}
        {data.model && <>{data.model} · </>}
        {data.created_at && <>run {dateTime(data.created_at.slice(0, 16))}</>}
      </p>
      {data.note && <p className="rounded-md bg-surface-2 px-3 py-2 text-xs text-muted">{data.note}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted">
            <th className="py-1.5 font-medium">Metric</th>
            {experiments.map(([key, e]) => (
              <th key={key} className="py-1.5 text-right font-medium">
                {e.url ? <a href={e.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-accent hover:underline">{e.name ?? key}<ExternalLink className="size-3" /></a> : (e.name ?? key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {keys.map((k) => (
            <tr key={k} className="border-b border-border">
              <td className="py-1.5">{label(k)}</td>
              {experiments.map(([key, e]) => (
                <td key={key} className="py-1.5 text-right tabular-nums">{fmt(k, e.metrics?.[k])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
