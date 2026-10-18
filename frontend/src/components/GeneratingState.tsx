import { useEffect, useState } from "react";
import { TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/trip";

const TIPS = [
  "Reading everyone's preferences together",
  "Balancing budgets and dates across the group",
  "Drafting day-by-day itineraries",
  "Matching destinations to what people love",
];

interface GeneratingStateProps {
  status: "generating" | "failed";
  /** Organizer view of a failure: the stored error text. */
  error?: string | null;
  /** Organizer view of a failure: shows a Retry button. Without it, the participant message is shown. */
  onRetry?: () => void;
  retrying?: boolean;
}

export function GeneratingState({ status, error, onRetry, retrying }: GeneratingStateProps) {
  const [tip, setTip] = useState(0);

  useEffect(() => {
    if (status !== "generating") return;
    const id = setInterval(() => {
      setTip((t) => (t + 1) % TIPS.length);
    }, 4000);
    return () => {
      clearInterval(id);
    };
  }, [status]);

  if (status === "failed") {
    return (
      <div
        role="alert"
        className="flex flex-col gap-3 rounded-xl border border-danger/30 bg-danger-subtle p-5"
      >
        <div className="flex items-center gap-2 font-medium text-danger">
          <TriangleAlert className="size-4" aria-hidden="true" />
          Itinerary generation failed
        </div>
        <p className="text-sm text-foreground">
          {onRetry
            ? (error ?? "Something went wrong while generating itineraries.")
            : "The organizer has been notified and can retry. Check back soon."}
        </p>
        {onRetry && (
          <Button className="self-start" loading={retrying} onClick={onRetry}>
            Retry generation
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      role="status"
      className="flex flex-col items-center gap-5 rounded-xl border bg-surface px-5 py-12 text-center"
    >
      <div className="flex w-40 gap-1" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className={cn("h-1.5 flex-1 animate-pulse rounded-full bg-accent")}
            style={{ animationDelay: `${(i * 200).toString()}ms` }}
          />
        ))}
      </div>
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Building your options</h2>
        <p key={tip} className="mt-1 h-5 animate-fade-in text-sm text-muted-foreground">
          {TIPS[tip]}
        </p>
      </div>
      <p className="text-xs text-muted-foreground">
        Usually 20–60 seconds. This page updates automatically.
      </p>
    </div>
  );
}
