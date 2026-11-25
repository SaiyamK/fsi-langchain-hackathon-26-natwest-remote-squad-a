import * as RT from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

export const TooltipProvider = RT.Provider;

export function Tooltip({ content, children }: { content: ReactNode; children: ReactNode }) {
  return (
    <RT.Root delayDuration={200}>
      <RT.Trigger asChild>{children}</RT.Trigger>
      <RT.Portal>
        <RT.Content
          sideOffset={6}
          className="z-50 max-w-xs rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-text shadow-lg"
        >
          {content}
        </RT.Content>
      </RT.Portal>
    </RT.Root>
  );
}
