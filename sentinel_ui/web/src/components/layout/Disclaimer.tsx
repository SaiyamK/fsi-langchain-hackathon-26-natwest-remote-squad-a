export const DISCLAIMER = "Draft for analyst review, not legal, compliance or regulatory advice. Synthetic data only.";

export function Disclaimer() {
  return (
    <footer className="border-t border-border bg-surface px-4 py-1.5 text-center text-[11px] text-muted" role="contentinfo">
      {DISCLAIMER}
    </footer>
  );
}
