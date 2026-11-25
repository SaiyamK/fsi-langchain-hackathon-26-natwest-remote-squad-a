import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { TONE_CLASSES, type StatusMeta, type Tone } from "@/lib/status";

export function Badge({ tone, children, className }: { tone: Tone; children: ReactNode; className?: string }) {
  const t = TONE_CLASSES[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap [&_svg]:size-3.5",
        t.soft,
        t.text,
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Status pill: colour + icon + label, never colour alone (EX-9.2). */
export function StatusBadge({ meta, suffix, className }: { meta: StatusMeta; suffix?: ReactNode; className?: string }) {
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} className={className}>
      <Icon className={meta.spin ? "animate-spin" : undefined} aria-hidden />
      {meta.label}
      {suffix}
    </Badge>
  );
}
