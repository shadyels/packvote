import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { cn } from "@/lib/trip";
import type { Itinerary } from "@/types";

export const optionTitle = (o: Itinerary) => o.option_title ?? o.destination_name;

export const formatBudget = (o: Itinerary) =>
  `${o.currency} ${o.total_estimated_budget.toLocaleString()}`;

interface OptionCardProps {
  option: Itinerary;
  /** Final-round vote count, shown when defined. */
  votes?: number;
  winner?: boolean;
  /** Greyed out (a winner exists and this is not it). */
  dimmed?: boolean;
}

export function OptionCard({ option, votes, winner = false, dimmed = false }: OptionCardProps) {
  const [day, setDay] = useState<number | null>(null);
  const days = option.daily_itinerary;
  const current = day === null ? undefined : days[day];

  useEffect(() => {
    if (day === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") setDay((d) => (d === null ? d : Math.max(0, d - 1)));
      if (e.key === "ArrowRight")
        setDay((d) => (d === null ? d : Math.min(days.length - 1, d + 1)));
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  }, [day === null, days.length]); // eslint-disable-line react-hooks/exhaustive-deps -- only open/closed matters

  return (
    <article
      className={cn(
        "flex flex-col gap-3 rounded-xl border bg-surface p-4 transition-opacity",
        winner && "border-accent ring-1 ring-accent",
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
        <div className="flex shrink-0 flex-col items-end gap-1">
          {winner && (
            <Badge tone="success">
              <Check className="mr-1 size-3" aria-hidden="true" />
              Winner
            </Badge>
          )}
          {votes !== undefined && (
            <span className="text-sm text-muted-foreground tabular-nums">
              {votes} {votes === 1 ? "vote" : "votes"}
            </span>
          )}
        </div>
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
        <ul className="flex flex-wrap gap-1.5">
          {option.highlights.slice(0, 4).map((h) => (
            <li key={h} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {h}
            </li>
          ))}
        </ul>
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
        title={
          current ? `Day ${current.day_number.toString()} · ${current.title}` : optionTitle(option)
        }
        description={optionTitle(option)}
        className="sm:max-w-xl"
      >
        {current && day !== null && (
          <div className="flex flex-col gap-4">
            {day === 0 && option.match_reasoning && (
              <p className="rounded-lg bg-muted p-3 text-sm text-muted-foreground">
                {option.match_reasoning}
              </p>
            )}
            <ul className="flex flex-col divide-y divide-border">
              {current.activities.map((a, i) => (
                <li key={`${a.title}-${i.toString()}`} className="flex gap-3 py-3 first:pt-0">
                  <span className="w-16 shrink-0 text-xs text-muted-foreground tabular-nums">
                    {a.time}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{a.title}</p>
                    <p className="text-sm text-muted-foreground">{a.description}</p>
                    {a.estimated_cost !== null && (
                      <p className="mt-1 text-xs text-muted-foreground tabular-nums">
                        ~{option.currency}
                        {a.estimated_cost.toLocaleString()} per person
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                size="sm"
                disabled={day === 0}
                onClick={() => {
                  setDay(day - 1);
                }}
              >
                <ArrowLeft className="size-4" aria-hidden="true" />
                Previous
              </Button>
              <span className="text-sm text-muted-foreground tabular-nums" aria-live="polite">
                {day + 1} of {days.length}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={day === days.length - 1}
                onClick={() => {
                  setDay(day + 1);
                }}
              >
                Next
                <ArrowRight className="size-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </article>
  );
}
