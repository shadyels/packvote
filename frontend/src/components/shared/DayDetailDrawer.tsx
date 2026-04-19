import { useEffect, useState } from "react";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Dialog, DialogOverlay, DialogPortal } from "@/components/ui/dialog";
import type { DayItinerary } from "@/types";

interface DayDetailDrawerProps {
  days: DayItinerary[];
  initialDayIndex: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currency?: string;
}

export function DayDetailDrawer({
  days,
  initialDayIndex,
  open,
  onOpenChange,
  currency = "",
}: DayDetailDrawerProps) {
  const [currentDayIndex, setCurrentDayIndex] = useState(initialDayIndex);

  // Sync currentDayIndex when the drawer opens with a new initialDayIndex
  useEffect(() => {
    if (open) {
      setCurrentDayIndex(initialDayIndex);
    }
  }, [open, initialDayIndex]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") {
        setCurrentDayIndex((i) => Math.max(0, i - 1));
      } else if (e.key === "ArrowRight") {
        setCurrentDayIndex((i) => Math.min(days.length - 1, i + 1));
      }
      // Escape is handled by the Dialog primitive
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, days.length]);

  const day = days[currentDayIndex];
  const isFirst = currentDayIndex === 0;
  const isLast = currentDayIndex === days.length - 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogPortal>
        <DialogOverlay />
        {/* Note: animate-slide-down exit won't complete on mobile — @base-ui removes
            the node immediately on close. Enter animation (animate-slide-up) works correctly. */}
        <DialogPrimitive.Popup
          className={cn(
            // Mobile: bottom sheet
            "fixed bottom-0 left-0 right-0 z-50 rounded-t-xl bg-background",
            "max-h-[85vh] overflow-y-auto",
            "outline-none",
            "ring-1 ring-foreground/10",
            // Desktop: centered modal
            "sm:bottom-auto sm:left-1/2 sm:right-auto sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:max-w-md sm:rounded-xl",
            // Animations — mobile slide-up/down, desktop fade+zoom
            "data-open:animate-slide-up data-closed:animate-slide-down",
            "sm:data-open:animate-in sm:data-open:fade-in-0 sm:data-open:zoom-in-95",
            "sm:data-closed:animate-out sm:data-closed:fade-out-0 sm:data-closed:zoom-out-95"
          )}
        >
          <div className="p-4">
            {/* Drag handle — mobile affordance */}
            <div className="w-10 h-1 bg-muted rounded-full mx-auto mb-4 sm:hidden" />

            {/* Header */}
            <div className="relative flex items-center justify-between mb-4">
              {/* Left nav arrow */}
              <button
                onClick={() => {
                  setCurrentDayIndex((i) => Math.max(0, i - 1));
                }}
                disabled={isFirst}
                aria-label="Previous day"
                className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-full transition-colors",
                  isFirst
                    ? "text-muted-foreground/30 cursor-not-allowed"
                    : "text-foreground hover:bg-muted"
                )}
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {/* Title */}
              <DialogPrimitive.Title className="font-semibold text-sm text-center flex-1 px-2 truncate">
                Day {day.day_number} &middot; {day.title}
              </DialogPrimitive.Title>

              {/* Right nav arrow */}
              <button
                onClick={() => {
                  setCurrentDayIndex((i) => Math.min(days.length - 1, i + 1));
                }}
                disabled={isLast}
                aria-label="Next day"
                className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-full transition-colors",
                  isLast
                    ? "text-muted-foreground/30 cursor-not-allowed"
                    : "text-foreground hover:bg-muted"
                )}
              >
                <ChevronRight className="w-4 h-4" />
              </button>

            </div>

            {/* Activity timeline */}
            {day.activities.length > 0 ? (
              <div className="relative pl-6">
                {/* Vertical line */}
                <div className="absolute left-2.5 top-1 bottom-1 w-px bg-brand/30" />

                <div className="space-y-4">
                  {day.activities.map((act, i) => (
                    <div key={`${String(i)}-${act.time ?? ""}-${act.title}`} className="relative">
                      {/* Orange dot marker */}
                      <div className="absolute -left-[18px] top-1.5 w-2 h-2 rounded-full bg-brand" />

                      <div className="space-y-0.5">
                        {act.time && (
                          <p className="text-xs text-muted-foreground font-medium">
                            {act.time}
                          </p>
                        )}
                        <p className="text-sm font-semibold text-foreground">
                          {act.title}
                        </p>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {act.description}
                        </p>
                        {act.estimated_cost !== null && (
                          <p className="text-xs text-brand font-medium">
                            ~{currency}
                            {act.estimated_cost} per person
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No activities listed for this day.
              </p>
            )}
          </div>
        </DialogPrimitive.Popup>
      </DialogPortal>
    </Dialog>
  );
}
