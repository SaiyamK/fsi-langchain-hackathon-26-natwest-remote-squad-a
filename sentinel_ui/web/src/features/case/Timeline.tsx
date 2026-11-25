import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { money, shortDate } from "@/lib/format";
import type { CaseDetail } from "@/types/api";
import type { Selection } from "./NetworkGraph";
import type { useReplay } from "./useReplay";

const MOMENT_TONE = { first_in: "bg-accent", peak: "bg-memory", cash_out: "bg-flagged", flagged: "bg-review" } as const;

/** Transfers in time order, linked to the graph, with replay controls and key moments (FR-6.1..6.3, EX-5.4). */
export function Timeline({
  detail,
  replay,
  selection,
  onSelect,
}: {
  detail: CaseDetail;
  replay: ReturnType<typeof useReplay>;
  selection: Selection;
  onSelect: (s: Selection) => void;
}) {
  const { timeline, moments } = detail;
  const name = (id: string) => detail.nodes.find((n) => n.id === id)?.label ?? id;
  const start = timeline[0] ? Date.parse(`${timeline[0].timestamp}Z`) : 0;
  const end = timeline.length ? Date.parse(`${timeline[timeline.length - 1]!.timestamp}Z`) : 1;
  const x = (ts: string) => ((Date.parse(`${ts}Z`) - start) / Math.max(end - start, 1)) * 100;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="icon" variant="ghost" onClick={() => replay.step(-1)} aria-label="Step back"><SkipBack /></Button>
        {replay.playing ? (
          <Button size="sm" onClick={replay.pause}><Pause /> Pause</Button>
        ) : (
          <Button size="sm" variant="default" onClick={replay.play}><Play /> Replay</Button>
        )}
        <Button size="icon" variant="ghost" onClick={() => replay.step(1)} aria-label="Step forward"><SkipForward /></Button>
        <div className="inline-flex rounded-md border border-border p-0.5" role="group" aria-label="Replay speed">
          {[1, 2, 4].map((s) => (
            <button key={s} onClick={() => replay.setSpeed(s)} aria-pressed={replay.speed === s} className={cn("rounded px-1.5 text-xs", replay.speed === s ? "bg-surface-2 font-medium" : "text-muted")}>
              {s}×
            </button>
          ))}
        </div>
        <span className="text-xs text-muted tabular-nums">
          {replay.cursor + 1} / {timeline.length} transfers {replay.frame.now && `· ${shortDate(replay.frame.now)}`}
        </span>
        {replay.caption && <span className="ml-auto rounded-md bg-accent px-2 py-0.5 text-xs font-medium text-white" role="status">{replay.caption}</span>}
      </div>
      <div className="relative h-6">
        <input
          type="range"
          min={-1}
          max={timeline.length - 1}
          value={replay.cursor}
          onChange={(e) => replay.seek(Number(e.target.value))}
          aria-label="Scrub through the transfers"
          className="absolute inset-x-0 top-1 w-full accent-[var(--accent)]"
        />
        {moments.map((m) => (
          <span key={m.kind + m.timestamp} title={`${shortDate(m.timestamp)}: ${m.label}`} className={cn("absolute top-4 size-2 -translate-x-1 rounded-full", MOMENT_TONE[m.kind])} style={{ left: `${Math.min(100, Math.max(0, x(m.timestamp)))}%` }} />
        ))}
      </div>
      <ol className="max-h-40 overflow-y-auto rounded-md border border-border text-xs">
        {timeline.map((t, i) => {
          const active = i === replay.cursor;
          const selected = selection?.kind === "edge" && selection.id === t.edge_id;
          return (
            <li key={t.transaction_id}>
              <button
                onClick={() => { replay.seek(i); onSelect({ kind: "edge", id: t.edge_id }); }}
                className={cn("grid w-full grid-cols-[6.5rem_1fr_5rem] gap-2 px-2 py-1 text-left hover:bg-surface-2", i > replay.cursor && "opacity-40", (active || selected) && "bg-surface-2 font-medium")}
              >
                <span className="text-muted tabular-nums">{shortDate(t.timestamp)}</span>
                <span className="truncate">{name(t.source)} → {name(t.target)}</span>
                <span className="text-right tabular-nums">{money(t.amount)}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
