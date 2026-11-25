import { FileText, Gavel } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { DecisionForm } from "@/features/alerts/DecisionForm";
import { money } from "@/lib/format";
import { useLive } from "@/stores/live";
import type { CaseDetail } from "@/types/api";
import { SarSheet } from "./SarSheet";

/** Clear or escalate with a note; open the SAR draft (FR-9). */
export function AnalystActions({ detail }: { detail: CaseDetail }) {
  const rows = useLive((s) => s.txById);
  const [sar, setSar] = useState<string | null>(null);
  const pending = detail.summary.transaction_ids.filter((id) => rows[id]?.status === "needs_analyst");
  const flagged = detail.summary.transaction_ids.filter((id) => rows[id]?.status === "flagged" && rows[id]?.decided_by === "agent");
  const target = pending[0] ?? flagged[flagged.length - 1];

  return (
    <div className="space-y-3">
      {target ? (
        <div className="space-y-2">
          <p className="text-sm">
            <Gavel className="mr-1 inline size-4 text-muted" />
            {pending.length ? (
              <>The agents are waiting for you on <span className="font-mono text-xs">{target}</span> ({money(rows[target]!.amount)}).</>
            ) : (
              <>Review the agents’ escalation of <span className="font-mono text-xs">{target}</span>. Your note is saved as a precedent.</>
            )}
          </p>
          <DecisionForm key={target} transactionId={target} />
        </div>
      ) : (
        <p className="text-sm text-muted">No decision pending on this case.</p>
      )}
      {detail.sar_ids.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {detail.sar_ids.map((id) => (
            <Button key={id} size="sm" onClick={() => setSar(id)}>
              <FileText /> SAR draft {id.replace("SAR-", "")}
            </Button>
          ))}
        </div>
      )}
      {detail.summary.verdict === "escalate" && !detail.sar_ids.length && (
        <p className="text-xs text-muted">No SAR draft yet: the SAR writer runs after an escalation is recorded.</p>
      )}
      <Dialog open={sar !== null} onOpenChange={(o) => !o && setSar(null)}>{sar && <SarSheet sarId={sar} />}</Dialog>
    </div>
  );
}
