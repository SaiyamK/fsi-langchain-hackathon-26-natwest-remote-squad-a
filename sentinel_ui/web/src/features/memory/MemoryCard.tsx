import { BrainCircuit, Save, ShieldX } from "lucide-react";
import { motion } from "motion/react";
import { cn } from "@/lib/cn";
import { dateTime, monthsBetween } from "@/lib/format";
import { usePrefs } from "@/stores/prefs";
import type { MemoryCard as Card } from "@/types/api";

/** One visual identity for memory (EX-2.5): purple, a brain icon, and the words "Sentinel remembers". */
export function MemoryCard({ card, asOf, compact }: { card: Card; asOf?: string | null; compact?: boolean }) {
  const reduced = usePrefs((s) => s.reducedMotion);
  const overridden = card.kind === "overridden";
  const Icon = card.kind === "saved" ? Save : overridden ? ShieldX : BrainCircuit;
  const ago = card.created_at && asOf ? monthsBetween(card.created_at, asOf.slice(0, 10)) : null;
  const who = card.analyst && card.analyst !== "seed" ? card.analyst : "an analyst";

  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn("rounded-md border border-memory/40 bg-memory-soft text-sm", compact ? "px-2 py-1.5" : "px-3 py-2")}
      role="note"
      aria-label={`Memory: ${card.kind}`}
    >
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 size-4 shrink-0 text-memory" aria-hidden />
        <div className="min-w-0">
          {card.kind === "saved" ? (
            <p>
              <span className="font-semibold text-memory">Saved to memory:</span> applies to {card.scope || card.key}
              {card.expires_at && <> until {dateTime(card.expires_at)}</>}.
            </p>
          ) : (
            <p>
              <span className="font-semibold text-memory">Sentinel remembers:</span> {overridden ? "an earlier" : ""} {card.note ? "cleared" : "decided"}
              {ago !== null && <> {ago === 0 ? "this month" : `${ago} month${ago === 1 ? "" : "s"} ago`}</>} by {who}
              {card.note && <> — “{card.note}”</>}.
              {!overridden && card.expires_at && <> Valid until {dateTime(card.expires_at)}.</>}
            </p>
          )}
          {overridden && (
            <p className="mt-1">
              <span className="rounded bg-flagged px-1.5 py-px text-[11px] font-bold tracking-wide text-white">OVERRIDDEN</span>{" "}
              <span className="text-flagged">{card.reason.replace(/^hard red flag: /, "Hard red flag: ")}</span>
            </p>
          )}
          {!compact && card.scope && card.kind !== "saved" && <p className="mt-0.5 text-xs text-muted">Scope: {card.scope}</p>}
        </div>
      </div>
    </motion.div>
  );
}

export function MemoryBadge({ cards }: { cards: Card[] }) {
  if (!cards.length) return null;
  const overridden = cards.some((c) => c.kind === "overridden");
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-memory-soft px-1.5 py-0.5 text-[11px] font-medium text-memory" title="Memory used">
      <BrainCircuit className="size-3" aria-hidden />
      {overridden ? "overridden" : cards.some((c) => c.kind === "saved") ? "saved" : "precedent"}
    </span>
  );
}
