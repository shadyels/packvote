import { Badge } from "@/components/ui/badge";
import { STATUS_CONFIG } from "@/lib/trip-status";
import { useDestinationImage } from "@/lib/unsplash";
import type { TripPublicInfo } from "@/types";

interface TripHeaderProps {
  trip: TripPublicInfo;
}

function HeroBanner({ destination }: { destination: string }) {
  const { imageUrl, gradient, isLoading } = useDestinationImage(destination);

  if (isLoading) {
    return <div className="h-40 w-full animate-shimmer rounded-xl" />;
  }

  return (
    <div className="relative h-40 w-full overflow-hidden rounded-xl">
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={destination}
          className="h-full w-full object-cover"
        />
      ) : (
        <div className="h-full w-full" style={{ background: gradient }} />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
      <p className="absolute bottom-3 left-4 text-white font-semibold text-lg drop-shadow">
        {destination}
      </p>
    </div>
  );
}

export function TripHeader({ trip }: TripHeaderProps) {
  const statusCfg = STATUS_CONFIG[trip.status];

  return (
    <div className="space-y-3">
      {/* Hero banner when destination is known */}
      {trip.destination && <HeroBanner destination={trip.destination} />}

      <div className="flex items-start justify-between gap-3">
        <h1 className="text-xl font-bold text-foreground leading-tight">
          {trip.title}
        </h1>
        <Badge className={`shrink-0 text-xs ${statusCfg.className}`}>
          {statusCfg.label}
        </Badge>
      </div>

      {/* Only show destination text if no hero banner */}
      {!trip.destination && (
        <p className="text-sm text-muted-foreground">Destination: TBD</p>
      )}

      {(trip.proposed_start_date ?? trip.proposed_end_date) && (
        <p className="text-xs text-muted-foreground">
          {trip.proposed_start_date ?? "?"} → {trip.proposed_end_date ?? "?"}
        </p>
      )}
    </div>
  );
}
