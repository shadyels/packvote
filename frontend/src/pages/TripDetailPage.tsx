import { useParams, Link } from "react-router-dom";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { useTripDetail } from "@/hooks/useTripDetail";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TripOverviewSection } from "@/components/dashboard/TripOverviewSection";
import { ParticipantsSection } from "@/components/dashboard/ParticipantsSection";
import { ItinerariesSection } from "@/components/dashboard/ItinerariesSection";
import { VotingSection } from "@/components/dashboard/VotingSection";

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <div className="flex gap-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-8 w-24 rounded-md" />
        ))}
      </div>
      <Skeleton className="h-64 w-full rounded-lg" />
    </div>
  );
}

export default function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const id = parseInt(tripId ?? "0", 10);

  const {
    trip,
    participants,
    itineraries,
    votingResults,
    isLoading,
    error,
    refetch,
  } = useTripDetail(id);

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <Toaster theme="light" />
      <div className="max-w-6xl mx-auto">
        {/* Back link */}
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-black/50 hover:text-black mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to dashboard
        </Link>

        {/* Error */}
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

        {isLoading && <DetailSkeleton />}

        {!isLoading && trip && (
          <>
            <div className="flex items-start justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold text-black">{trip.title}</h1>
                <p className="text-black/50 text-sm mt-1">
                  {trip.destination ?? "Destination: surprise me"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={refetch}
                className="text-black/40 hover:text-black hover:bg-transparent"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </Button>
            </div>

            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <Tabs defaultValue="overview">
                <TabsList variant="line" className="w-full justify-start px-6 py-2 border-b border-border rounded-none gap-4">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="participants">
                    Participants
                    <span className="ml-1.5 text-xs opacity-50">
                      ({participants.length})
                    </span>
                  </TabsTrigger>
                  <TabsTrigger value="itineraries">
                    Itineraries
                    <span className="ml-1.5 text-xs opacity-50">
                      ({itineraries.length})
                    </span>
                  </TabsTrigger>
                  <TabsTrigger value="voting">Voting</TabsTrigger>
                </TabsList>

                <TabsContent value="overview" className="p-6">
                  <TripOverviewSection
                    trip={trip}
                    itineraries={itineraries}
                    participants={participants}
                    onRefetch={refetch}
                  />
                </TabsContent>

                <TabsContent value="participants" className="p-6">
                  <ParticipantsSection participants={participants} trip={trip} />
                </TabsContent>

                <TabsContent value="itineraries" className="p-6">
                  <ItinerariesSection
                    itineraries={itineraries}
                    votingResults={votingResults}
                    winnerId={trip.winner_itinerary_id ?? null}
                  />
                </TabsContent>

                <TabsContent value="voting" className="p-6">
                  <VotingSection
                    votingResults={votingResults}
                    itineraries={itineraries}
                  />
                </TabsContent>
              </Tabs>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
