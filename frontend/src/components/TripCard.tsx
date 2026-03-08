import type { TripSummary } from "@/types";

interface TripCardProps {
  trip: TripSummary;
}

export default function TripCard({ trip }: TripCardProps) {
  // TODO: flesh out in admin dashboard step
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h3 className="font-semibold text-cream">{trip.title}</h3>
      <p className="text-sm text-muted-foreground">{trip.destination ?? "Surprise me"}</p>
      <span className="mt-2 inline-block rounded-full bg-accent/20 px-2 py-0.5 text-xs text-accent">
        {trip.status}
      </span>
    </div>
  );
}
