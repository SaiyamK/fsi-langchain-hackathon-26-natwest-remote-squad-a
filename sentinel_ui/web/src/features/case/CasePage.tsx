import { ArrowLeft, ChevronLeft, ChevronRight, Network, ScrollText, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Empty } from "@/components/ui/empty";
import { Switch } from "@/components/ui/switch";
import { confidence, money, patternLabel } from "@/lib/format";
import { CASE_STATUS } from "@/lib/status";
import { useLive } from "@/stores/live";
import { usePrefs } from "@/stores/prefs";
import { sortCases } from "@/stores/reducer";
import type { CaseDetail, Role } from "@/types/api";
import { AccountSheet } from "./AccountSheet";
import { AgentExplanation } from "./AgentExplanation";
import { AnalystActions } from "./AnalystActions";
import { AuditPanel } from "./AuditPanel";
import { BalanceStrips } from "./BalanceStrips";
import { Legend } from "./Legend";
import { MetricsPanel } from "./MetricsPanel";
import { NetworkGraph, type Selection } from "./NetworkGraph";
import { Timeline } from "./Timeline";
import { useCase } from "./useCase";
import { useReplay } from "./useReplay";

function CaseNav({ caseId }: { caseId: string }) {
  const cases = useLive((s) => s.cases);
  const order = useMemo(() => sortCases(Object.values(cases)).map((c) => c.case_id), [cases]);
  const i = order.indexOf(caseId);
  const prev = i > 0 ? order[i - 1] : undefined;
  const next = i >= 0 && i < order.length - 1 ? order[i + 1] : undefined;
  return (
    <div className="flex items-center gap-1">
      <Button asChild size="sm" variant="ghost"><Link to="/queue"><ArrowLeft /> Queue</Link></Button>
      <Button asChild size="icon" variant="ghost" aria-disabled={!prev}>
        <Link to={prev ? `/cases/${encodeURIComponent(prev)}` : "#"} aria-label="Previous case"><ChevronLeft /></Link>
      </Button>
      <Button asChild size="icon" variant="ghost" aria-disabled={!next}>
        <Link to={next ? `/cases/${encodeURIComponent(next)}` : "#"} aria-label="Next case"><ChevronRight /></Link>
      </Button>
    </div>
  );
}

function CaseBody({ detail }: { detail: CaseDetail }) {
  const { reducedMotion, autoplayReplay, setAutoplayReplay, edgeLabels, setEdgeLabels } = usePrefs();
  const [params, setParams] = useSearchParams();
  const replay = useReplay(detail.timeline, detail.moments, autoplayReplay && detail.timeline.length > 1, reducedMotion);
  const nodeParam = params.get("node");
  const [selection, setSelection] = useState<Selection>(nodeParam ? { kind: "node", id: nodeParam } : null);
  const select = (s: Selection) => {
    setSelection(s);
    const next = new URLSearchParams(params);
    if (s?.kind === "node") next.set("node", s.id);
    else next.delete("node");
    setParams(next, { replace: true });
  };
  const selectedNode = selection?.kind === "node" ? detail.nodes.find((n) => n.id === selection.id) : undefined;
  const selectedEdge = selection?.kind === "edge" ? detail.edges.find((e) => e.id === selection.id) : undefined;
  const roles = [...new Set(detail.nodes.map((n) => n.role))] as Role[];
  const s = detail.summary;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 xl:grid-cols-[minmax(0,1fr)_20rem_24rem]">
      <div className="flex min-w-0 flex-col gap-3">
        <Card className="flex flex-col">
          <CardHeader
            title={detail.finding}
            icon={<Network />}
            action={
              <div className="flex items-center gap-3">
                <Switch checked={edgeLabels} onCheckedChange={setEdgeLabels} label="Amounts" />
                <Switch checked={autoplayReplay} onCheckedChange={setAutoplayReplay} label="Auto-replay" />
              </div>
            }
          />
          <div className="relative aspect-[2/1] max-h-[30rem] w-full">
            <NetworkGraph detail={detail} frame={replay.frame} replaying={replay.replaying} selection={selection} onSelect={select} edgeLabels={edgeLabels} reduced={reducedMotion} />
          </div>
          <div className="border-t border-border px-3 py-2"><Legend roles={roles} /></div>
          {selectedEdge && (
            <div className="border-t border-border px-3 py-2 text-xs">
              <p className="mb-1 font-medium">
                {detail.nodes.find((n) => n.id === selectedEdge.source)?.label} → {detail.nodes.find((n) => n.id === selectedEdge.target)?.label}: {money(selectedEdge.amount)} in {selectedEdge.count} transfer{selectedEdge.count > 1 ? "s" : ""}
              </p>
              <ul className="grid gap-x-4 sm:grid-cols-2">
                {selectedEdge.transfers.map((t) => (
                  <li key={t.transaction_id} className="flex gap-2 tabular-nums"><span className="font-mono text-muted">{t.transaction_id}</span>{t.timestamp.replace("T", " ")} · {money(t.amount, t.currency)} · {t.txn_type.replace(/_/g, " ")}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
        <Card className="space-y-3 p-3">
          <Timeline detail={detail} replay={replay} selection={selection} onSelect={select} />
          <BalanceStrips detail={detail} now={replay.replaying ? replay.frame.now : null} />
        </Card>
      </div>

      <MetricsPanel detail={detail} />

      <div className="flex min-h-0 flex-col gap-3">
        <Card>
          <CardHeader title="Analyst decision" icon={<Sparkles />} />
          <div className="p-3"><AnalystActions detail={detail} /></div>
        </Card>
        <Card className="min-h-0 flex-1 overflow-y-auto">
          <CardHeader title={`Agent explanation · ${patternLabel(s.pattern)}`} />
          <div className="p-3"><AgentExplanation detail={detail} /></div>
        </Card>
        <Card>
          <CardHeader title="Audit" icon={<ScrollText />} />
          <div className="max-h-56 overflow-y-auto p-3"><AuditPanel detail={detail} /></div>
        </Card>
      </div>

      <Dialog open={Boolean(selectedNode)} onOpenChange={(o) => !o && select(null)}>
        {selectedNode && <AccountSheet node={selectedNode} asOf={detail.as_of} />}
      </Dialog>
    </div>
  );
}

/** One case on one screen (CV-1..CV-3): graph, metrics, timeline, explanation, actions. */
export function CasePage() {
  const { caseId = "" } = useParams();
  const summary = useLive((s) => s.cases[caseId]);
  const markOpened = usePrefs((s) => s.markOpened);
  const reduced = usePrefs((s) => s.reducedMotion);
  const navigate = useNavigate();
  const { data, isLoading, error } = useCase(caseId);

  useEffect(() => {
    if (summary) markOpened(caseId, summary.updated_seq);
  }, [caseId, summary, markOpened]);

  if (!summary) {
    return (
      <Empty icon={<Network />} title="Case not in this session">
        It may belong to a reset session or not be flagged yet. <button className="text-accent underline" onClick={() => navigate("/queue")}>Back to the queue</button>
      </Empty>
    );
  }

  return (
    <motion.div key={caseId} initial={reduced ? false : { opacity: 0, scale: 0.99 }} animate={{ opacity: 1, scale: 1 }} className="flex h-full min-h-0 flex-col overflow-y-auto">
      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-surface px-3 py-2">
        <CaseNav caseId={caseId} />
        <h1 className="text-lg font-semibold">{patternLabel(summary.pattern)} · {summary.lead_name}</h1>
        <span className="font-mono text-xs text-muted">{summary.case_id}</span>
        <StatusBadge meta={CASE_STATUS[summary.status]} />
        <span className="text-sm">
          verdict <strong className={summary.verdict === "escalate" ? "text-flagged" : "text-cleared"}>{summary.verdict ?? "—"}</strong> · confidence {confidence(summary.confidence)}
        </span>
        <span className="ml-auto text-sm text-muted tabular-nums">{money(summary.total_amount)} · {summary.accounts} accounts</span>
      </div>
      {error ? (
        <Empty title="Could not load the case">{(error as Error).message}</Empty>
      ) : isLoading || !data ? (
        <Empty title="Loading case…" />
      ) : (
        <CaseBody key={caseId} detail={data} />
      )}
    </motion.div>
  );
}
