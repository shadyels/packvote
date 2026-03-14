import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TripSummary, TripStatus } from "@/types";

const STATUS_CONFIG: Record<
  TripStatus,
  { label: string; className: string }
> = {
  CREATED: {
    label: "Created",
    className: "bg-zinc-700 text-zinc-200 hover:bg-zinc-700",
  },
  COLLECTING_PREFERENCES: {
    label: "Collecting",
    className: "bg-blue-900/60 text-blue-300 hover:bg-blue-900/60",
  },
  GENERATING: {
    label: "Generating",
    className: "bg-amber-900/60 text-amber-300 hover:bg-amber-900/60",
  },
  VOTING: {
    label: "Voting",
    className: "bg-accent/20 text-accent hover:bg-accent/20",
  },
  ITERATING: {
    label: "Iterating",
    className: "bg-purple-900/60 text-purple-300 hover:bg-purple-900/60",
  },
  FINALIZED: {
    label: "Finalized",
    className: "bg-green-900/60 text-green-300 hover:bg-green-900/60",
  },
};

interface TripCardProps {
  trip: TripSummary;
}

export default function TripCard({ trip }: TripCardProps) {
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
      className="bg-card border-border cursor-pointer transition-colors hover:border-accent/50"
      onClick={() => navigate(`/dashboard/trip/${trip.id.toString()}`)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-cream text-base leading-tight">
            {trip.title}
          </CardTitle>
          <Badge className={`shrink-0 text-xs ${statusCfg.className}`}>
            {statusCfg.label}
          </Badge>
        </div>
        <p className="text-sm text-cream/50 mt-0.5">
          {trip.destination ?? "Destination: surprise me"}
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Preferences progress */}
        <div>
          <div className="flex justify-between text-xs text-cream/50 mb-1">
            <span>Preferences</span>
            <span>
              {trip.preferences_submitted_count}/{trip.participant_count}
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        <p className="text-xs text-cream/40">
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
