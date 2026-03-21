import { useSearchParams } from "react-router-dom";
import { MapPin, RefreshCw } from "lucide-react";
import { useTrips } from "@/hooks/useTrips";
import TripCard from "@/components/TripCard";
import { CreateTripDialog } from "@/components/CreateTripDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import type { TripSummary } from "@/types";

// ---------------------------------------------------------------------------
// Preview mock data — remove before deploying to prod
// ---------------------------------------------------------------------------
const MOCK_TRIPS: TripSummary[] = [
  { id: 1, trip_code: "SPRNG26A", title: "Spring Group Trip 2026", destination: "Lisbon, Portugal",
    status: "VOTING", participant_count: 4, preferences_submitted_count: 4, created_at: "2026-03-01T10:00:00Z" },
  { id: 2, trip_code: "SUMM26B", title: "Summer Beach Escape", destination: "Algarve, Portugal",
    status: "COLLECTING_PREFERENCES", participant_count: 6, preferences_submitted_count: 3, created_at: "2026-03-10T09:00:00Z" },
  { id: 3, trip_code: "WKND26C", title: "Weekend City Break", destination: null,
    status: "GENERATING", participant_count: 3, preferences_submitted_count: 3, created_at: "2026-03-15T14:00:00Z" },
  { id: 4, trip_code: "AUTM26D", title: "Autumn Adventure", destination: "Kyoto, Japan",
    status: "FINALIZED", participant_count: 5, preferences_submitted_count: 5, created_at: "2026-02-20T08:00:00Z" },
  { id: 5, trip_code: "NEWYR26E", title: "New Year's Eve Trip", destination: "Barcelona, Spain",
    status: "CREATED", participant_count: 8, preferences_submitted_count: 0, created_at: "2026-03-18T11:00:00Z" },
];

function DashboardPreview() {
  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Preview banner */}
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-dashed border-border bg-card p-3">
          <span className="text-xs text-muted-foreground">Preview mode — mock data only</span>
        </div>

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-black">My Trips</h1>
            <p className="text-black/50 mt-1 text-sm">Plan and manage your group adventures</p>
          </div>
          <CreateTripDialog onCreated={() => { /* no-op in preview */ }} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {MOCK_TRIPS.map((trip) => (
            <TripCard key={trip.id} trip={trip} />
          ))}
        </div>
      </div>
    </div>
  );
}
// ---------------------------------------------------------------------------

function TripCardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <Skeleton className="h-5 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-1.5 w-full rounded-full" />
      <Skeleton className="h-3 w-1/4" />
    </div>
  );
}

function DashboardPageInner() {
  const { trips, isLoading, error, refetch } = useTrips();

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-black">My Trips</h1>
            <p className="text-black/50 mt-1 text-sm">
              Plan and manage your group adventures
            </p>
          </div>
          <CreateTripDialog onCreated={refetch} />
        </div>

        {/* Error state */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 mb-6 flex items-center justify-between">
            <p className="text-sm text-red-600">{error}</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={refetch}
              className="text-red-600 hover:text-red-700 hover:bg-transparent"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Retry
            </Button>
          </div>
        )}

        {/* Loading skeletons */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <TripCardSkeleton key={i} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && trips.length === 0 && (
          <div className="text-center py-24 space-y-4">
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                <MapPin className="h-8 w-8 text-black/30" />
              </div>
            </div>
            <h2 className="text-xl font-semibold text-black">No trips yet</h2>
            <p className="text-black/50 text-sm max-w-xs mx-auto">
              Create your first trip to start collecting preferences and
              planning with your group.
            </p>
            <div className="mt-4">
              <CreateTripDialog onCreated={refetch} />
            </div>
          </div>
        )}

        {/* Trip grid */}
        {!isLoading && trips.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {trips.map((trip) => (
              <TripCard key={trip.id} trip={trip} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [searchParams] = useSearchParams();
  if (searchParams.get("preview") === "true") return <DashboardPreview />;
  return <DashboardPageInner />;
}
