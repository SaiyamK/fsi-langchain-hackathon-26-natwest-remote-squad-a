import * as RD from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export const Dialog = RD.Root;
export const DialogTrigger = RD.Trigger;

/** A right-hand drawer (transaction detail, legend, SAR draft). */
export function Sheet({
  title,
  description,
  children,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <RD.Portal>
      <RD.Overlay className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[1px]" />
      <RD.Content
        className={cn(
          "fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-border bg-surface shadow-2xl focus:outline-none",
          className,
        )}
      >
        <div className="flex items-start gap-2 border-b border-border px-4 py-3">
          <div className="min-w-0">
            <RD.Title className="text-base font-semibold">{title}</RD.Title>
            {description ? (
              <RD.Description className="text-sm text-muted">{description}</RD.Description>
            ) : (
              <RD.Description className="sr-only">Details</RD.Description>
            )}
          </div>
          <RD.Close className="ml-auto rounded-md p-1 text-muted hover:bg-surface-2" aria-label="Close">
            <X className="size-4" />
          </RD.Close>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4">{children}</div>
      </RD.Content>
    </RD.Portal>
  );
}
