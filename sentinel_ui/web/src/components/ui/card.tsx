import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-border bg-surface", className)} {...props} />;
}

export function CardHeader({
  title,
  icon,
  action,
  className,
}: {
  title: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-2 border-b border-border px-3 py-2", className)}>
      {icon && <span className="text-muted [&_svg]:size-4">{icon}</span>}
      <h2 className="text-sm font-semibold">{title}</h2>
      {action && <div className="ml-auto flex items-center gap-1">{action}</div>}
    </div>
  );
}
