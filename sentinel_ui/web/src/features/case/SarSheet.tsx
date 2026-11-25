import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { Sheet } from "@/components/ui/dialog";
import { DISCLAIMER } from "@/components/layout/Disclaimer";
import { api } from "@/lib/api";
import { patternLabel } from "@/lib/format";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-1">
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">{title}</h3>
      {children}
    </section>
  );
}

/** The SAR draft written by the sar-writer agent, as a readable document with the stamp (FR-9.4, EX-6.1). */
export function SarSheet({ sarId }: { sarId: string }) {
  const { data, isLoading, error } = useQuery({ queryKey: ["sar", sarId], queryFn: () => api.sar(sarId) });
  return (
    <Sheet title={<span className="inline-flex items-center gap-2"><FileText className="size-4" />SAR draft {sarId}</span>} description="Written by the SAR writer agent from the gathered evidence only" className="max-w-2xl">
      <p className="mb-4 rounded-md border-2 border-dashed border-flagged px-3 py-2 text-center text-sm font-semibold text-flagged">{DISCLAIMER}</p>
      {isLoading && <p className="text-sm text-muted">Loading…</p>}
      {error && <p className="text-sm text-flagged">{(error as Error).message}</p>}
      {data && (
        <article className="space-y-4 text-sm">
          <Section title="Subject"><p>{data.subject}</p></Section>
          <Section title="Pattern"><p>{patternLabel(data.pattern)}</p></Section>
          <Section title="Narrative"><p className="leading-relaxed">{data.narrative}</p></Section>
          <Section title="Timeline"><ol className="list-decimal space-y-0.5 pl-5">{data.timeline.map((t) => <li key={t}>{t}</li>)}</ol></Section>
          <Section title="Evidence"><ul className="list-disc space-y-0.5 pl-5">{data.evidence.map((e) => <li key={e}>{e}</li>)}</ul></Section>
          <Section title="Precedents cited or overridden">
            {data.precedents_cited_or_overridden.length ? <ul className="list-disc pl-5">{data.precedents_cited_or_overridden.map((p) => <li key={p}>{p}</li>)}</ul> : <p className="text-muted">None</p>}
          </Section>
          <p className="border-t border-border pt-2 text-xs text-muted">{data.disclaimer}</p>
        </article>
      )}
    </Sheet>
  );
}
