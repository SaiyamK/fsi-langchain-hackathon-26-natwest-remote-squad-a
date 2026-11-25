import { ROLE_META } from "@/lib/status";
import type { Role } from "@/types/api";
import { ROLE_FILL } from "./roles";

/** Every graph style explained (FR-4.3, EX-9.3). */
export function Legend({ roles }: { roles: Role[] }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted" aria-label="Legend">
      {roles.map((r) => (
        <li key={r} className="inline-flex items-center gap-1" title={ROLE_META[r]?.description}>
          <span className="size-2.5 rounded-full" style={{ background: ROLE_FILL[r] }} aria-hidden />
          {ROLE_META[r]?.label ?? r}
        </li>
      ))}
      <li className="inline-flex items-center gap-1">
        <span className="size-3 rounded-full border-2 border-dashed border-flagged" aria-hidden /> Hard red flag
      </li>
      <li className="inline-flex items-center gap-1">
        <svg width="10" height="12" aria-hidden><path d="M1 1 v10 M1 1 h7 l-2 3 l2 3 h-7" fill="var(--flagged)" stroke="var(--flagged)" /></svg> Red flag fired
      </li>
      <li className="inline-flex items-center gap-1">
        <span className="size-3 rounded-full border border-dashed border-muted" aria-hidden /> Other bank
      </li>
      <li>Line width = amount · fill = net balance during replay</li>
    </ul>
  );
}
