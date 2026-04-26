import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { STATUS_CONFIG } from "@/lib/trip-status";
import type { TripSummary } from "@/types";

interface TripCardProps {
  trip: TripSummary;
  href?: string;
}

export default function TripCard({ trip, href }: TripCardProps) {
  const navigate = useNavigate();
  const statusCfg = STATUS_CONFIG[trip.status];
  const progressPercent =
    trip.participant_count > 0
      ? Math.round(
          (trip.preferences_submitted_count / trip.participant_count) * 100
        )
      : 0;

  return (
    <Card
      className="bg-card border-border cursor-pointer transition-all duration-200 hover:border-brand/40 hover:shadow-md hover:-translate-y-0.5 border-t-2"
      style={{ borderTopColor: statusCfg.className.includes("brand") ? "#FF6B2C" : undefined }}
      onClick={() => { navigate(href ?? `/dashboard/trip/${trip.id.toString()}`); }}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-black text-base leading-tight">
            {trip.title}
          </CardTitle>
          <Badge className={`shrink-0 text-xs ${statusCfg.className}`}>
            {statusCfg.label}
          </Badge>
        </div>
        <p className="text-sm text-black/50 mt-0.5">
          {trip.destination ?? "Destination: surprise me"}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Preferences progress */}
        <div>
          <div className="flex justify-between text-xs text-black/50 mb-1">
            <span>Preferences</span>
            <span>
              {trip.preferences_submitted_count}/{trip.participant_count}
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-brand transition-all"
              style={{ width: `${progressPercent.toString()}%` }}
            />
          </div>
        </div>

        <p className="text-xs text-black/40">
          {new Date(trip.created_at).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </p>
      </CardContent>
    </Card>
  );
}
