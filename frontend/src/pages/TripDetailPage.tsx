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
import { AILogsSection } from "@/components/dashboard/AILogsSection";

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
    aiLogs,
    isLoading,
    error,
    refetch,
  } = useTripDetail(id);

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <Toaster theme="dark" />
      <div className="max-w-6xl mx-auto">
        {/* Back link */}
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-cream/50 hover:text-cream mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to dashboard
        </Link>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-900 bg-red-950/30 p-4 mb-6 flex items-center justify-between">
            <p className="text-sm text-red-400">{error}</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={refetch}
              className="text-red-400 hover:text-red-300 hover:bg-transparent"
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
                <h1 className="text-3xl font-bold text-cream">{trip.title}</h1>
                <p className="text-cream/50 text-sm mt-1">
                  {trip.destination ?? "Destination: surprise me"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={refetch}
                className="text-cream/40 hover:text-cream hover:bg-transparent"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </Button>
            </div>

            <Tabs defaultValue="overview">
              <TabsList className="bg-muted border border-border mb-6 h-auto flex-wrap gap-0.5">
                <TabsTrigger
                  value="overview"
                  className="text-cream/60 data-[state=active]:text-cream data-[state=active]:bg-card"
                >
                  Overview
                </TabsTrigger>
                <TabsTrigger
                  value="participants"
                  className="text-cream/60 data-[state=active]:text-cream data-[state=active]:bg-card"
                >
                  Participants
                  <span className="ml-1.5 text-xs text-cream/40">
                    ({participants.length})
                  </span>
                </TabsTrigger>
                <TabsTrigger
                  value="itineraries"
                  className="text-cream/60 data-[state=active]:text-cream data-[state=active]:bg-card"
                >
                  Itineraries
                  <span className="ml-1.5 text-xs text-cream/40">
                    ({itineraries.length})
                  </span>
                </TabsTrigger>
                <TabsTrigger
                  value="voting"
                  className="text-cream/60 data-[state=active]:text-cream data-[state=active]:bg-card"
                >
                  Voting
                </TabsTrigger>
                <TabsTrigger
                  value="ai-logs"
                  className="text-cream/60 data-[state=active]:text-cream data-[state=active]:bg-card"
                >
                  AI Logs
                  <span className="ml-1.5 text-xs text-cream/40">
                    ({aiLogs.length})
                  </span>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview">
                <TripOverviewSection
                  trip={trip}
                  itineraries={itineraries}
                  onRefetch={refetch}
                />
              </TabsContent>

              <TabsContent value="participants">
                <ParticipantsSection participants={participants} />
              </TabsContent>

              <TabsContent value="itineraries">
                <ItinerariesSection
                  itineraries={itineraries}
                  votingResults={votingResults}
                  winnerId={trip.winner_itinerary_id ?? null}
                />
              </TabsContent>

              <TabsContent value="voting">
                <VotingSection
                  votingResults={votingResults}
                  itineraries={itineraries}
                />
              </TabsContent>

              <TabsContent value="ai-logs">
                <AILogsSection logs={aiLogs} />
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>
    </div>
  );
}
