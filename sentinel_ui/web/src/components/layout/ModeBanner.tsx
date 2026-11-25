import { CloudOff, History, Radio } from "lucide-react";
import { dateTime } from "@/lib/format";
import { useLive } from "@/stores/live";

/** DEC-003: a replay is always labelled; offline mode says the agents aren't running. */
export function ModeBanner() {
  const session = useLive((s) => s.session);
  if (!session) return null;
  if (session.mode === "replay" && session.replay) {
    const live = session.live_transactions.length;
    return (
      <div className="flex items-center gap-2 border-b border-memory/30 bg-memory-soft px-4 py-1.5 text-xs text-memory" role="note">
        <History className="size-3.5" aria-hidden />
        <strong>REPLAY:</strong> agent results recorded from the live run at {dateTime(session.replay.recorded_at.slice(0, 16))} UTC
        {session.replay.model && <> on {session.replay.model}</>} ({session.replay.investigations} investigations).
        {live > 0 && <> {live} transaction{live > 1 ? "s run" : " runs"} live.</>} Each verdict links to its LangSmith trace.
      </div>
    );
  }
  if (session.mode === "offline") {
    return (
      <div className="flex items-center gap-2 border-b border-review/30 bg-review-soft px-4 py-1.5 text-xs text-review" role="note">
        <CloudOff className="size-3.5" aria-hidden />
        <strong>Agents offline:</strong> no model key is configured, so the rules tier runs and every flagged transaction goes to the analyst. Add the LangSmith key to the repo-root .env to run the agents.
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2 border-b border-border px-4 py-1 text-xs text-muted">
      <Radio className="size-3.5 text-cleared" aria-hidden /> {session.mode === "record" ? "Live, recording for replay" : "Live"} · {session.model}
    </div>
  );
}
