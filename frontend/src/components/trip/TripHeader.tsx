import { Badge } from "@/components/ui/badge";
import { STATUS_CONFIG } from "@/lib/trip-status";
import type { TripPublicInfo } from "@/types";

interface TripHeaderProps {
  trip: TripPublicInfo;
}

export function TripHeader({ trip }: TripHeaderProps) {
  const statusCfg = STATUS_CONFIG[trip.status];

  return (
    <div className="space-y-1">
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-xl font-bold text-foreground leading-tight">
          {trip.title}
        </h1>
        <Badge className={`shrink-0 text-xs ${statusCfg.className}`}>
          {statusCfg.label}
        </Badge>
      </div>
      {trip.destination && (
        <p className="text-sm text-muted-foreground">{trip.destination}</p>
      )}
      {(trip.proposed_start_date ?? trip.proposed_end_date) && (
        <p className="text-xs text-muted-foreground">
          {trip.proposed_start_date ?? "?"} → {trip.proposed_end_date ?? "?"}
        </p>
      )}
    </div>
  );
}
