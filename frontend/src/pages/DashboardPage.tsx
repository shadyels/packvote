import { RefreshCw } from "lucide-react";
import { useTrips } from "@/hooks/useTrips";
import TripCard from "@/components/TripCard";
import { CreateTripDialog } from "@/components/CreateTripDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

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

export default function DashboardPage() {
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
            <p className="text-5xl">🗺️</p>
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
