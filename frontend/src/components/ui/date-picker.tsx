import { useState } from "react";
import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import { Calendar } from "@/components/ui/calendar";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DatePickerProps {
  value: Date | undefined;
  onChange: (date: Date | undefined) => void;
  placeholder?: string;
  id?: string;
  className?: string;
  disabled?: (date: Date) => boolean;
  /** Month to open the calendar on. Falls back to value, then current month. */
  defaultMonth?: Date;
  toYear?: number;
}

export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a date",
  id,
  className,
  disabled,
  defaultMonth,
  toYear,
}: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const today = new Date();

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          id={id}
          type="button"
          className={cn(
            buttonVariants({ variant: "outline" }),
            "w-full justify-start text-left font-normal bg-card border-border text-black",
            !value && "text-black/40",
            className,
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4 shrink-0 opacity-50" />
          {value ? format(value, "MMM d, yyyy") : placeholder}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-50 rounded-md border border-border bg-card shadow-md p-0"
          align="start"
          sideOffset={4}
        >
          <Calendar
            mode="single"
            selected={value}
            onSelect={(date) => {
              onChange(date);
              setOpen(false);
            }}
            disabled={disabled}
            captionLayout="dropdown"
            startMonth={new Date(today.getFullYear(), today.getMonth())}
            endMonth={new Date(toYear ?? today.getFullYear() + 5, 11)}
            defaultMonth={defaultMonth ?? value ?? today}
            autoFocus
          />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
