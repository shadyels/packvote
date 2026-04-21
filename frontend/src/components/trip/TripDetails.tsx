import { CalendarDays, MapPin, StickyNote } from "lucide-react";
import { format, parseISO } from "date-fns";
import type { TripPublicInfo } from "@/types";

interface TripDetailsProps {
  trip: TripPublicInfo;
}

function formatDateRange(start: string | null, end: string | null): string | null {
  if (!start && !end) return null;
  const fmt = (d: string) => format(parseISO(d), "MMM d, yyyy");
  if (start && end) return `${fmt(start)} – ${fmt(end)}`;
  if (start) return `From ${fmt(start)}`;
  if (end) return `Until ${fmt(end)}`;
  return null;
}

export function TripDetails({ trip }: TripDetailsProps) {
  const dateRange = formatDateRange(trip.proposed_start_date, trip.proposed_end_date);
  const hasDetails = trip.destination || dateRange || trip.notes;

  if (!hasDetails) return null;

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Organizer's Proposal
      </p>

      <div className="space-y-2.5">
        {trip.destination && (
          <div className="flex items-start gap-2.5">
            <MapPin className="h-4 w-4 text-brand mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground leading-none mb-0.5">Destination</p>
              <p className="text-sm font-semibold text-foreground">{trip.destination}</p>
            </div>
          </div>
        )}

        {dateRange && (
          <div className="flex items-start gap-2.5">
            <CalendarDays className="h-4 w-4 text-brand mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground leading-none mb-0.5">Proposed Dates</p>
              <p className="text-sm font-semibold text-foreground">{dateRange}</p>
            </div>
          </div>
        )}

        {trip.notes && (
          <div className="flex items-start gap-2.5">
            <StickyNote className="h-4 w-4 text-brand mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-muted-foreground leading-none mb-0.5">Notes from organizer</p>
              <p className="text-sm text-foreground leading-relaxed">{trip.notes}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
