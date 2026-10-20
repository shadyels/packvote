import type { ReactNode } from "react";
import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/trip";

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

/**
 * Controlled modal. Bottom sheet below `sm`, centered card from `sm` up.
 * base-ui sets data-starting-style / data-ending-style, so enter/exit are plain CSS transitions.
 */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  className,
}: DialogProps) {
  return (
    <BaseDialog.Root open={open} onOpenChange={onOpenChange}>
      <BaseDialog.Portal>
        <BaseDialog.Backdrop className="fixed inset-0 bg-overlay transition-opacity duration-200 data-ending-style:opacity-0 data-ending-style:duration-150 data-starting-style:opacity-0" />
        <BaseDialog.Popup
          className={cn(
            "fixed inset-x-0 bottom-0 max-h-[90dvh] overflow-y-auto rounded-t-2xl border-t bg-surface p-5 shadow-xl transition-[transform,opacity] duration-200 data-ending-style:translate-y-full data-ending-style:duration-150 data-starting-style:translate-y-full",
            "sm:top-1/2 sm:right-auto sm:bottom-auto sm:left-1/2 sm:w-[calc(100%-2rem)] sm:max-w-lg sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-xl sm:border sm:data-ending-style:-translate-y-1/2 sm:data-ending-style:scale-95 sm:data-ending-style:opacity-0 sm:data-starting-style:-translate-y-1/2 sm:data-starting-style:scale-95 sm:data-starting-style:opacity-0",
            className
          )}
        >
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <BaseDialog.Title className="text-base font-semibold">{title}</BaseDialog.Title>
              {description && (
                <BaseDialog.Description className="mt-1 text-sm text-muted-foreground">
                  {description}
                </BaseDialog.Description>
              )}
            </div>
            <BaseDialog.Close
              aria-label="Close"
              className="-mt-2 -mr-2 inline-flex size-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="size-4" aria-hidden="true" />
            </BaseDialog.Close>
          </div>
          {children}
        </BaseDialog.Popup>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  );
}
