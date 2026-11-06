import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { FlapWord, StatusFlap } from "@/components/ui/Flap";
import { cn } from "@/lib/trip";
import type { DailyActivity, Itinerary } from "@/types";

export const optionTitle = (o: Itinerary) => o.option_title ?? o.destination_name;

export const formatBudget = (o: Itinerary) =>
  `${o.currency} ${o.total_estimated_budget.toLocaleString()}`;

const pad2 = (n: number) => n.toString().padStart(2, "0");

function DayButton({
  n,
  state,
  onSelect,
}: {
  n: number;
  state: "past" | "current" | "next";
  onSelect: () => void;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const current = state === "current";
  useEffect(() => {
    // jsdom has no scrollIntoView
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
    if (current) ref.current?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [current]);
  return (
    <button
      ref={ref}
      type="button"
      aria-label={`Day ${n.toString()}`}
      aria-current={current ? "step" : undefined}
      onClick={onSelect}
      className={cn(
        // pt-[9px] under a 1px rule matches pt-2 under the 2px rule, so the numerals share a baseline.
        "flex h-11 w-full min-w-11 items-start font-mono text-xs font-medium tracking-wider tabular-nums",
        state === "past" && "border-t border-foreground pt-[9px]",
        current && "border-t-2 border-accent-ink pt-2 font-semibold",
        state === "next" &&
          "border-t border-border pt-[9px] text-muted-foreground hover:text-foreground"
      )}
    >
      {pad2(n)}
    </button>
  );
}

// aria-disabled (not `disabled`) at the ends so focus stays on the button that was just pressed.
const endClass =
  "aria-disabled:cursor-default aria-disabled:opacity-50 aria-disabled:hover:bg-transparent aria-disabled:active:scale-100";

/** Gate strip for days: passed days a thin foreground rule, the current day a heavier accent-ink rule and bold numeral. */
function DayStrip({
  day,
  count,
  onSelect,
}: {
  day: number;
  count: number;
  onSelect: (d: number) => void;
}) {
  return (
    <nav aria-label="Days" className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        aria-label="Previous day"
        aria-disabled={day === 0}
        className={endClass}
        onClick={() => {
          if (day > 0) onSelect(day - 1);
        }}
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
      </Button>
      <ol className="flex min-w-0 flex-1 [scrollbar-width:none] gap-1 overflow-x-auto">
        {Array.from({ length: count }, (_, i) => (
          <li key={i} className="min-w-11 flex-1 shrink-0">
            <DayButton
              n={i + 1}
              state={i < day ? "past" : i === day ? "current" : "next"}
              onSelect={() => {
                onSelect(i);
              }}
            />
          </li>
        ))}
      </ol>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Next day"
        aria-disabled={day === count - 1}
        className={endClass}
        onClick={() => {
          if (day < count - 1) onSelect(day + 1);
        }}
      >
        <ArrowRight className="size-4" aria-hidden="true" />
      </Button>
      <p className="sr-only" aria-live="polite">
        Day {day + 1} of {count}
      </p>
    </nav>
  );
}

// Node centre from the top of a stop: row 1 is a 16px slot label or a 24px title; later stops add the 20px gap.
const GAP = 20;

/** Transit-line diagram: square nodes joined by a 2px rule; slot label only when it changes. */
function Route({ activities }: { activities: DailyActivity[] }) {
  return (
    <ol className="flex flex-col">
      {activities.map((a, i) => {
        const first = i === 0;
        const last = i === activities.length - 1;
        const label = a.time !== null && a.time !== activities[i - 1]?.time ? a.time : null;
        const centre = (first ? 0 : GAP) + (label ? 8 : 12);
        return (
          <li key={`${a.title}-${i.toString()}`} className="relative pl-6 not-first:pt-5">
            {!(first && last) && (
              <span
                aria-hidden="true"
                className="absolute left-1 w-0.5 bg-foreground"
                style={{
                  top: first ? centre : 0,
                  bottom: last ? `calc(100% - ${centre.toString()}px)` : 0,
                }}
              />
            )}
            <span
              aria-hidden="true"
              className="absolute left-0 size-2.5 rounded-sm bg-foreground"
              style={{ top: centre - 5 }}
            />
            {label && (
              <p className="font-mono text-xs leading-4 font-medium tracking-wider text-muted-foreground uppercase">
                {label}
              </p>
            )}
            <p className="text-base leading-6 font-semibold">{a.title}</p>
            <p className="text-sm text-muted-foreground">{a.description}</p>
          </li>
        );
      })}
    </ol>
  );
}

interface OptionCardProps {
  option: Itinerary;
  winner?: boolean;
  /** Greyed out (a winner exists and this is not it). */
  dimmed?: boolean;
}

export function OptionCard({ option, winner = false, dimmed = false }: OptionCardProps) {
  const [day, setDay] = useState<number | null>(null);
  const days = option.daily_itinerary;
  const current = day === null ? undefined : days[day];

  const isOpen = day !== null;
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.metaKey || e.ctrlKey) return; // Alt+Left is browser Back
      if (e.key === "ArrowLeft") setDay((d) => (d === null ? d : Math.max(0, d - 1)));
      if (e.key === "ArrowRight")
        setDay((d) => (d === null ? d : Math.min(days.length - 1, d + 1)));
    };
    // Capture phase: the dialog popup stops keydown from bubbling to window.
    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("keydown", onKey, true);
    };
  }, [isOpen, days.length]);

  return (
    <article
      className={cn(
        "flex flex-col gap-3 rounded-xl border bg-surface p-4 transition-opacity",
        winner && "border-success",
        dimmed && "opacity-60"
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold tracking-tight">{optionTitle(option)}</h3>
          {option.option_title && (
            <p className="text-sm text-muted-foreground">{option.destination_name}</p>
          )}
        </div>
        {winner && (
          <span className="shrink-0">
            <StatusFlap tone="success">Winner</StatusFlap>
          </span>
        )}
      </header>

      <p className="line-clamp-3 text-sm text-muted-foreground">{option.destination_description}</p>

      <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Budget</dt>
          <dd className="font-medium tabular-nums">{formatBudget(option)}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="text-muted-foreground">Length</dt>
          <dd className="font-medium tabular-nums">
            {days.length} {days.length === 1 ? "day" : "days"}
          </dd>
        </div>
      </dl>

      {option.highlights.length > 0 && (
        <p className="text-sm text-muted-foreground">{option.highlights.slice(0, 4).join(" · ")}</p>
      )}

      {option.match_reasoning && (
        <p className="max-w-[65ch] text-sm text-muted-foreground">{option.match_reasoning}</p>
      )}

      {days.length > 0 && (
        <Button
          variant="secondary"
          size="sm"
          className="self-start"
          onClick={() => {
            setDay(0);
          }}
        >
          Day-by-day
        </Button>
      )}

      <Dialog
        open={day !== null}
        onOpenChange={(open) => {
          if (!open) setDay(null);
        }}
        title={optionTitle(option)}
        // Fixed height so the strip never moves between days; only the route scrolls.
        className="flex h-[90dvh] flex-col overflow-hidden sm:h-[min(90dvh,44rem)] sm:max-w-xl"
      >
        {current && day !== null && (
          <div className="flex min-h-0 flex-1 flex-col gap-5">
            <DayStrip day={day} count={days.length} onSelect={setDay} />
            <div className="flex shrink-0 flex-col gap-3">
              <FlapWord text={`DAY ${pad2(day + 1)}`} label={null} size="board" />
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <h3 className="min-w-0 text-2xl font-semibold tracking-tight">{current.title}</h3>
                <p className="text-sm text-muted-foreground">{option.destination_name}</p>
              </div>
            </div>
            <div key={day} className="min-h-0 flex-1 [scrollbar-gutter:stable] overflow-y-auto">
              <Route activities={current.activities} />
            </div>
          </div>
        )}
      </Dialog>
    </article>
  );
}
