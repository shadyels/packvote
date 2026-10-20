import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { STATUS, formatTimestamp } from "@/lib/trip";
import type { TripSummary } from "@/types";

interface TripRowProps {
  trip: TripSummary;
  to: string;
  /** Router state passed to the link (e.g. { from: "dashboard-invited" }). */
  linkState?: unknown;
}

/** Fixed height so list skeletons can reserve the same space (h-20). */
export function TripRow({ trip, to, linkState }: TripRowProps) {
  const status = STATUS[trip.status];
  return (
    <Link
      to={to}
      state={linkState}
      className="flex h-20 items-center gap-3 px-3 transition-colors hover:bg-muted focus-visible:bg-muted"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold">{trip.title}</span>
          <Badge tone={status.tone}>{status.label}</Badge>
        </div>
        <p className="mt-1 truncate text-sm text-muted-foreground">
          {trip.destination || "Surprise me"}
        </p>
      </div>
      <div className="shrink-0 text-right text-xs text-muted-foreground tabular-nums">
        <p>
          {trip.preferences_submitted_count}/{trip.participant_count} preferences
        </p>
        <p className="mt-1">{formatTimestamp(trip.created_at)}</p>
      </div>
      <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
    </Link>
  );
}
