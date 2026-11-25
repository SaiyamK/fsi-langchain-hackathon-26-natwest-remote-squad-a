import { compactMoney } from "@/lib/format";
import type { CaseDetail } from "@/types/api";
import { peakBalance } from "./replay";
import { ROLE_FILL } from "./roles";

/** Net flow over time for each mule and the hub: pass-through shows as a rise and a quick fall (FR-6.4). */
export function BalanceStrips({ detail, now }: { detail: CaseDetail; now: string | null }) {
  const accounts = detail.nodes.filter((n) => detail.balances[n.id]?.length);
  if (!accounts.length) return null;
  const all = accounts.flatMap((n) => detail.balances[n.id]!.map((p) => Date.parse(`${p.timestamp}Z`)));
  const t0 = Math.min(...all);
  const t1 = Math.max(...all, t0 + 1);
  const W = 160;
  const H = 28;
  const nowX = now ? ((Date.parse(`${now}Z`) - t0) / (t1 - t0)) * W : null;

  return (
    <div>
      <p className="mb-1 text-[11px] text-muted">Net flow since the case window opened (no balance data in the source, so this is in minus out)</p>
      <ul className="grid grid-cols-2 gap-x-4 gap-y-1 xl:grid-cols-3">
        {accounts.map((n) => {
          const pts = detail.balances[n.id]!;
          const peak = peakBalance(pts);
          const path = pts
            .map((p, i) => {
              const x = ((Date.parse(`${p.timestamp}Z`) - t0) / (t1 - t0)) * W;
              const y = H - 2 - (Math.max(p.balance, 0) / peak) * (H - 4);
              return `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ");
          const last = pts[pts.length - 1]!.balance;
          return (
            <li key={n.id} className="flex items-center gap-2 text-xs">
              <span className="w-28 truncate" title={n.label}>{n.label}</span>
              <svg width={W} height={H} role="img" aria-label={`${n.label} net flow, peak ${compactMoney(peak)}, now ${compactMoney(last)}`}>
                <path d={path} fill="none" stroke={ROLE_FILL[n.role]} strokeWidth={1.5} />
                {nowX !== null && <line x1={nowX} x2={nowX} y1={0} y2={H} stroke="var(--accent)" strokeOpacity={0.5} />}
              </svg>
              <span className="text-muted tabular-nums">{compactMoney(peak)} → {compactMoney(last)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
