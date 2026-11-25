import type { ReactNode } from "react";

export function Empty({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center text-sm text-muted">
      {icon && <div className="text-muted/70 [&_svg]:size-8">{icon}</div>}
      <p className="font-medium text-text">{title}</p>
      {children && <div className="max-w-sm">{children}</div>}
    </div>
  );
}
