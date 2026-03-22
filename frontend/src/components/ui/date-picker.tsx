import { useState } from "react";
import { format, startOfDay, setMonth as dfSetMonth, setYear as dfSetYear, endOfMonth, isBefore } from "date-fns";
import { CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import { Calendar } from "@/components/ui/calendar";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type View = "days" | "months" | "years";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

interface DatePickerProps {
  value: Date | undefined;
  onChange: (date: Date | undefined) => void;
  placeholder?: string;
  id?: string;
  className?: string;
  disabled?: (date: Date) => boolean;
  /** Month to open the calendar on. Falls back to value, then current month. */
  defaultMonth?: Date;
}

export function DatePicker({
  value,
  onChange,
  placeholder = "Pick a date",
  id,
  className,
  disabled,
  defaultMonth,
}: DatePickerProps) {
  const today = new Date();

  const getInitial = () => defaultMonth ?? value ?? today;

  const [open, setOpen] = useState(false);
  const [view, setView] = useState<View>("days");
  const [viewDate, setViewDate] = useState<Date>(getInitial());
  const [yearRangeStart, setYearRangeStart] = useState(today.getFullYear());

  const handleOpenChange = (o: boolean) => {
    setOpen(o);
    if (o) {
      const init = defaultMonth ?? value ?? today;
      setView("days");
      setViewDate(init);
      setYearRangeStart(today.getFullYear());
    }
  };

  // A month is disabled if it ended before today
  const isMonthDisabled = (year: number, monthIndex: number) => {
    const end = endOfMonth(new Date(year, monthIndex, 1));
    return isBefore(end, startOfDay(today));
  };

  // A year is disabled if it's entirely in the past
  const isYearDisabled = (year: number) => {
    return isBefore(new Date(year, 11, 31), startOfDay(today));
  };

  const handleMonthSelect = (monthIndex: number) => {
    if (isMonthDisabled(viewDate.getFullYear(), monthIndex)) return;
    setViewDate(dfSetMonth(viewDate, monthIndex));
    setView("days");
  };

  const handleYearSelect = (year: number) => {
    if (isYearDisabled(year)) return;
    setViewDate(dfSetYear(viewDate, year));
    setView("months");
  };

  const viewYear = viewDate.getFullYear();
  const years = Array.from({ length: 12 }, (_, i) => yearRangeStart + i);

  const gridButtonClass = (isSelected: boolean, isDisabled: boolean) =>
    cn(
      "rounded-md py-2 text-sm font-normal transition-colors",
      isSelected
        ? "bg-brand text-white"
        : isDisabled
          ? "text-muted-foreground opacity-50 cursor-not-allowed"
          : "text-foreground hover:bg-accent hover:text-accent-foreground",
    );

  const navButtonClass = (isDisabled: boolean) =>
    cn(
      "inline-flex items-center justify-center h-7 w-7 rounded-md border border-border bg-transparent p-0 transition-colors",
      isDisabled
        ? "opacity-50 pointer-events-none"
        : "hover:bg-accent hover:text-accent-foreground",
    );

  return (
    <Popover.Root open={open} onOpenChange={handleOpenChange}>
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
          {view === "days" && (
            <Calendar
              mode="single"
              selected={value}
              onSelect={(date) => {
                onChange(date);
                setOpen(false);
              }}
              disabled={disabled}
              month={viewDate}
              onMonthChange={setViewDate}
              startMonth={new Date(today.getFullYear(), today.getMonth())}
              onCaptionClick={() => { setView("months"); }}
              autoFocus
            />
          )}

          {view === "months" && (
            <div className="p-3 w-[280px]">
              <div className="flex items-center justify-between mb-3 px-1">
                <button
                  type="button"
                  aria-label="Previous year"
                  disabled={viewYear <= today.getFullYear()}
                  onClick={() => { setViewDate(dfSetYear(viewDate, viewYear - 1)); }}
                  className={navButtonClass(viewYear <= today.getFullYear())}
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => { setView("years"); }}
                  className="text-sm font-semibold text-foreground hover:text-brand transition-colors"
                >
                  {viewYear}
                </button>
                <button
                  type="button"
                  aria-label="Next year"
                  onClick={() => { setViewDate(dfSetYear(viewDate, viewYear + 1)); }}
                  className={navButtonClass(false)}
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-1">
                {MONTH_NAMES.map((name, i) => {
                  const dis = isMonthDisabled(viewYear, i);
                  const isSelected = !!value && value.getMonth() === i && value.getFullYear() === viewYear;
                  return (
                    <button
                      key={name}
                      type="button"
                      disabled={dis}
                      onClick={() => { handleMonthSelect(i); }}
                      className={gridButtonClass(isSelected, dis)}
                    >
                      {name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {view === "years" && (
            <div className="p-3 w-[280px]">
              <div className="flex items-center justify-between mb-3 px-1">
                <button
                  type="button"
                  aria-label="Previous years"
                  disabled={yearRangeStart <= today.getFullYear()}
                  onClick={() => { setYearRangeStart((y) => y - 12); }}
                  className={navButtonClass(yearRangeStart <= today.getFullYear())}
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-sm font-semibold text-foreground">
                  {yearRangeStart} – {yearRangeStart + 11}
                </span>
                <button
                  type="button"
                  aria-label="Next years"
                  onClick={() => { setYearRangeStart((y) => y + 12); }}
                  className={navButtonClass(false)}
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
              <div className="grid grid-cols-3 gap-1">
                {years.map((year) => {
                  const dis = isYearDisabled(year);
                  const isSelected = !!value && value.getFullYear() === year;
                  return (
                    <button
                      key={year}
                      type="button"
                      disabled={dis}
                      onClick={() => { handleYearSelect(year); }}
                      className={gridButtonClass(isSelected, dis)}
                    >
                      {year}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
