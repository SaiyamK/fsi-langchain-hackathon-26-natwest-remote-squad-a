import { useEffect, useRef, useState } from "react";
import { useLive } from "@/stores/live";

/** When a network case first appears, link its rows in the stream for a few seconds (EX-16.3). */
export function useRelatedHighlight(ms = 5000): Set<string> {
  const cases = useLive((s) => s.cases);
  const seen = useRef<Set<string>>(new Set());
  const [ids, setIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fresh = Object.values(cases).filter((c) => c.kind === "network" && !seen.current.has(c.case_id));
    if (!fresh.length) return;
    for (const c of fresh) seen.current.add(c.case_id);
    setIds(new Set(fresh.flatMap((c) => c.related_transaction_ids)));
    const t = setTimeout(() => setIds(new Set()), ms);
    return () => clearTimeout(t);
  }, [cases, ms]);

  return ids;
}
