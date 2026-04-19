import { ChevronLeft, ChevronRight } from "lucide-react";
import { DayPicker } from "react-day-picker";
import { cn } from "@/lib/utils";

export type CalendarProps = React.ComponentProps<typeof DayPicker> & {
  onCaptionClick?: () => void;
};

export function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  components: componentsProp,
  onCaptionClick,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col sm:flex-row gap-4",
        month: "flex flex-col gap-4",
        month_caption: "flex justify-center pt-1 relative items-center w-full",
        caption_label: "text-sm font-medium text-foreground",
        nav: "flex items-center gap-1 absolute inset-x-0 top-1 justify-between px-1 z-10",
        button_previous: cn(
          "inline-flex items-center justify-center h-7 w-7 rounded-md border border-border bg-transparent p-0",
          "hover:bg-accent hover:text-accent-foreground",
          "disabled:pointer-events-none disabled:opacity-50",
        ),
        button_next: cn(
          "inline-flex items-center justify-center h-7 w-7 rounded-md border border-border bg-transparent p-0",
          "hover:bg-accent hover:text-accent-foreground",
          "disabled:pointer-events-none disabled:opacity-50",
        ),
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "text-muted-foreground rounded-md w-8 font-normal text-[0.8rem] text-center",
        week: "flex w-full mt-2",
        day: "relative p-0 text-center text-sm focus-within:relative focus-within:z-20",
        day_button: cn(
          "h-8 w-8 p-0 font-normal rounded-md",
          "hover:bg-accent hover:text-accent-foreground",
          "focus:outline-none focus:ring-2 focus:ring-brand/50",
          "aria-selected:opacity-100",
        ),
        selected: "bg-brand text-white hover:bg-brand hover:text-white focus:bg-brand focus:text-white rounded-md",
        today: "bg-accent text-accent-foreground",
        outside: "text-muted-foreground opacity-50 aria-selected:bg-accent/50 aria-selected:text-muted-foreground aria-selected:opacity-30",
        disabled: "text-muted-foreground opacity-50 cursor-not-allowed hover:bg-transparent",
        range_middle: "aria-selected:bg-accent aria-selected:text-accent-foreground",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation }) =>
          orientation === "left" ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          ),
        ...(onCaptionClick
          ? {
              CaptionLabel: ({ id, children }: { id?: string; children?: React.ReactNode }) => (
                <button
                  id={id}
                  type="button"
                  onClick={onCaptionClick}
                  className="text-sm font-semibold text-foreground hover:text-brand transition-colors cursor-pointer"
                >
                  {children}
                </button>
              ),
            }
          : {}),
        ...componentsProp,
      }}
      {...props}
    />
  );
}
