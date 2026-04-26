import { MapPin, RefreshCw } from "lucide-react";
import { useTrips } from "@/hooks/useTrips";
import { useInvitedTrips } from "@/hooks/useInvitedTrips";
import TripCard from "@/components/TripCard";
import { CreateTripDialog } from "@/components/CreateTripDialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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

function TripGrid({
  trips,
  isLoading,
  error,
  refetch,
  emptyTitle,
  emptyBody,
  hrefFn,
}: {
  trips: Parameters<typeof TripCard>[0]["trip"][];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
  emptyTitle: string;
  emptyBody: string;
  hrefFn?: (trip: Parameters<typeof TripCard>[0]["trip"]) => string;
}) {
  return (
    <>
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

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <TripCardSkeleton key={i} />
          ))}
        </div>
      )}

      {!isLoading && !error && trips.length === 0 && (
        <div className="text-center py-24 space-y-4">
          <div className="flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
              <MapPin className="h-8 w-8 text-black/30" />
            </div>
          </div>
          <h2 className="text-xl font-semibold text-black">{emptyTitle}</h2>
          <p className="text-black/50 text-sm max-w-xs mx-auto">{emptyBody}</p>
        </div>
      )}

      {!isLoading && trips.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {trips.map((trip) => (
            <TripCard
              key={trip.id}
              trip={trip}
              href={hrefFn ? hrefFn(trip) : undefined}
            />
          ))}
        </div>
      )}
    </>
  );
}

export default function DashboardPage() {
  const { trips, isLoading, error, refetch } = useTrips();
  const {
    trips: invitedTrips,
    isLoading: invitedLoading,
    error: invitedError,
    refetch: refetchInvited,
  } = useInvitedTrips();

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
          <CreateTripDialog onCreated={() => { refetch(); refetchInvited(); }} />
        </div>

        <Tabs defaultValue="created">
          <TabsList variant="line" className="w-full justify-start border-b border-border rounded-none gap-4 mb-6 bg-transparent px-0">
            <TabsTrigger value="created">
              Created
              <span className="ml-1.5 text-xs opacity-50">({trips.length})</span>
            </TabsTrigger>
            <TabsTrigger value="invited">
              Invited
              <span className="ml-1.5 text-xs opacity-50">({invitedTrips.length})</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="created">
            <TripGrid
              trips={trips}
              isLoading={isLoading}
              error={error}
              refetch={refetch}
              emptyTitle="No trips yet"
              emptyBody="Create your first trip to start collecting preferences and planning with your group."
            />
          </TabsContent>

          <TabsContent value="invited">
            <TripGrid
              trips={invitedTrips}
              isLoading={invitedLoading}
              error={invitedError}
              refetch={refetchInvited}
              emptyTitle="No invitations yet"
              emptyBody="When someone adds you to a trip, it'll show up here."
              hrefFn={(trip) => {
                const t = trip as typeof invitedTrips[number];
                return `/trip/${t.participant_token}`;
              }}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
