import { useMutation } from "@tanstack/react-query";
import { FastForward, Pause, Play, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { selectClock, useLive } from "@/stores/live";

const SPEEDS = [2, 8, 20, 60];

/** Start, pause, resume, speed, fast-forward and reset (LS-7, EX-8.4). */
export function StreamControls() {
  const session = useLive((s) => s.session);
  const clock = useLive(selectClock);
  const control = useMutation({ mutationFn: (fn: () => Promise<unknown>) => fn() });
  if (!session) return null;
  const { state } = session;
  const busy = control.isPending;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {state === "running" ? (
        <Button onClick={() => control.mutate(api.pause)} disabled={busy}>
          <Pause /> Pause
        </Button>
      ) : (
        <Button variant="default" onClick={() => control.mutate(state === "idle" ? api.start : api.resume)} disabled={busy || state === "finished"}>
          <Play /> {state === "idle" ? "Start" : "Resume"}
        </Button>
      )}
      <Button onClick={() => control.mutate(() => api.fastForward(300))} disabled={busy || state === "finished"} title="Release the next 10 months at once">
        <FastForward /> Fast-forward 10 months
      </Button>
      <label className="flex items-center gap-1 text-xs text-muted">
        Speed
        <select
          className="h-8 rounded-md border border-border bg-surface px-1.5 text-sm text-text"
          value={SPEEDS.includes(session.speed) ? session.speed : ""}
          onChange={(e) => control.mutate(() => api.speed(Number(e.target.value)))}
          aria-label="Transactions per second"
        >
          {!SPEEDS.includes(session.speed) && <option value="">{session.speed}/s</option>}
          {SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s} tx/s
            </option>
          ))}
        </select>
      </label>
      <Button variant="ghost" onClick={() => control.mutate(api.reset)} disabled={busy} title="Return the demo to its starting state">
        <RotateCcw /> Reset
      </Button>
      <span className="ml-auto text-xs text-muted tabular-nums" aria-live="polite">
        {state === "finished" ? "Stream finished" : state === "paused" ? "Paused" : state === "idle" ? "Ready" : "Streaming"} · now{" "}
        {dateTime(clock)}
      </span>
    </div>
  );
}
