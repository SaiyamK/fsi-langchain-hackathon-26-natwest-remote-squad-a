import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Flag } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Decision } from "@/types/api";

/** Clear or escalate, with a required note (FR-9.1). Shortcuts never bypass the note (EX-12.2). */
export function DecisionForm({
  transactionId,
  initial,
  compact,
  onDone,
}: {
  transactionId: string;
  initial?: Decision;
  compact?: boolean;
  onDone?: (decision: Decision) => void;
}) {
  const id = useId();
  const [note, setNote] = useState("");
  const [chosen, setChosen] = useState<Decision | null>(initial ?? null);
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (decision: Decision) => api.decide(transactionId, decision, note.trim()),
    onSuccess: (_, decision) => {
      void qc.invalidateQueries({ queryKey: ["case"] });
      onDone?.(decision);
    },
  });

  const submit = (decision: Decision) => {
    setChosen(decision);
    if (note.trim()) mutation.mutate(decision);
  };
  const missing = chosen !== null && !note.trim();

  return (
    <form className="space-y-2" onSubmit={(e) => e.preventDefault()}>
      <label htmlFor={id} className="sr-only">
        Analyst note (required)
      </label>
      <textarea
        id={id}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={compact ? 2 : 3}
        placeholder="Note for the audit file and future precedent (required)"
        aria-invalid={missing}
        aria-describedby={missing ? `${id}-err` : undefined}
        className="w-full resize-none rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm placeholder:text-muted/70 focus:border-accent focus:outline-none aria-[invalid=true]:border-flagged"
      />
      {missing && (
        <p id={`${id}-err`} className="text-xs text-flagged">
          Add a note to {chosen}.
        </p>
      )}
      {mutation.isError && <p className="text-xs text-flagged">Could not save: {mutation.error.message}</p>}
      <div className="flex gap-2">
        <Button type="button" variant="clear" size={compact ? "sm" : "md"} disabled={mutation.isPending} onClick={() => submit("clear")}>
          <CheckCircle2 /> Clear
        </Button>
        <Button type="button" variant="escalate" size={compact ? "sm" : "md"} disabled={mutation.isPending} onClick={() => submit("escalate")}>
          <Flag /> Escalate
        </Button>
      </div>
    </form>
  );
}
