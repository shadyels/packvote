import { useParams, Link, useSearchParams } from "react-router-dom";
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
import type { Trip, Participant, Itinerary, VotingResults, TripStatus } from "@/types";

// ---------------------------------------------------------------------------
// Preview mock data — remove before deploying to prod
// ---------------------------------------------------------------------------
const MOCK_ITINERARIES: Itinerary[] = [
  {
    id: 1, trip_id: 0, iteration_number: 1,
    destination_name: "Lisbon, Portugal",
    destination_description: "A sun-drenched capital full of pastel trams, hilltop viewpoints, and exceptional food.",
    daily_itinerary_json: JSON.stringify([
      { day_number: 1, title: "Arrival & Alfama", estimated_cost: 80, activities: [
        { time: "10:00 AM", title: "Alfama district walk", description: "Explore the oldest neighbourhood.", estimated_cost: 0 },
        { time: "1:00 PM", title: "Lunch at Mercado da Ribeira", description: "Time Out Market.", estimated_cost: 25 },
        { time: "4:00 PM", title: "Belém Tower & pastéis", description: "Iconic tower + custard tarts.", estimated_cost: 15 },
      ]},
    ]),
    total_estimated_budget: 1100, currency: "USD",
    match_reasoning: "Fits the group's budget and love of walkable cities with great food.",
    highlights: JSON.stringify(["Tram 28 ride", "Pastéis de Belém", "Fado dinner"]),
    model_used: "Qwen2.5-72B-Instruct", provider: "huggingface",
    created_at: "2026-03-01T10:00:00Z",
    estimated_cost: null, price_last_updated: null, price_source: null,
  },
  {
    id: 2, trip_id: 0, iteration_number: 1,
    destination_name: "Porto, Portugal",
    destination_description: "A compact port city known for wine cellars, baroque churches, and the Douro riverfront.",
    daily_itinerary_json: JSON.stringify([
      { day_number: 1, title: "Ribeira & Wine", estimated_cost: 90, activities: [
        { time: "11:00 AM", title: "Livraria Lello bookshop", description: "One of the world's most beautiful bookshops.", estimated_cost: 5 },
        { time: "2:00 PM", title: "Port wine tasting", description: "Cross the bridge for cellar tours.", estimated_cost: 30 },
        { time: "6:00 PM", title: "Sunset at Miradouro da Serra do Pilar", description: "Best view over the river.", estimated_cost: 0 },
      ]},
    ]),
    total_estimated_budget: 950, currency: "USD",
    match_reasoning: "More affordable option, great for wine lovers and photography.",
    highlights: JSON.stringify(["Port wine cellars", "Douro riverfront", "Azulejo tiles"]),
    model_used: "Qwen2.5-72B-Instruct", provider: "huggingface",
    created_at: "2026-03-01T10:00:00Z",
    estimated_cost: null, price_last_updated: null, price_source: null,
  },
];

const MOCK_PARTICIPANTS: Participant[] = [
  { id: 1, trip_id: 0, email: "alex@example.com", name: "Alex Kim", preferences_submitted: true, created_at: "2026-03-01T10:00:00Z" },
  { id: 2, trip_id: 0, email: "jordan@example.com", name: "Jordan Lee", preferences_submitted: true, created_at: "2026-03-01T10:00:00Z" },
  { id: 3, trip_id: 0, email: "sam@example.com", name: "Sam Rivera", preferences_submitted: false, created_at: "2026-03-01T10:00:00Z" },
  { id: 4, trip_id: 0, email: "taylor@example.com", name: "Taylor Moss", preferences_submitted: true, created_at: "2026-03-01T10:00:00Z" },
];

const MOCK_VOTING_RESULTS: VotingResults = {
  trip_id: 0, iteration_number: 1,
  rounds: [
    { round_number: 1, results: { 1: 3, 2: 1 }, eliminated_option_id: 2, winner_id: null },
    { round_number: 2, results: { 1: 4, 2: 0 }, eliminated_option_id: null, winner_id: 1 },
  ],
  winner_id: 1, is_complete: true,
};

function buildMockTrip(status: string): Trip {
  const s = status as TripStatus;
  return {
    id: 0, trip_code: "SPRNG26A", creator_id: 99,
    title: "Spring Group Trip 2026", destination: "Lisbon, Portugal",
    proposed_start_date: "2026-05-10", proposed_end_date: "2026-05-17",
    num_options: 2, status: s,
    current_iteration: 1, max_iterations: 10,
    winner_itinerary_id: s === "FINALIZED" ? 1 : null,
    created_at: "2026-03-01T10:00:00Z",
  };
}

const PREVIEW_STATES = ["collecting", "generating", "voting", "finalized"] as const;
type PreviewState = typeof PREVIEW_STATES[number];

const STATUS_MAP: Record<PreviewState, TripStatus> = {
  collecting: "COLLECTING_PREFERENCES",
  generating: "GENERATING",
  voting: "VOTING",
  finalized: "FINALIZED",
};

function TripDetailPreview({
  preview,
  setSearchParams,
}: {
  preview: PreviewState;
  setSearchParams: (p: Record<string, string>) => void;
}) {
  const status = STATUS_MAP[preview];
  const trip = buildMockTrip(status);
  const itineraries = status === "VOTING" || status === "FINALIZED" ? MOCK_ITINERARIES : [];
  const votingResults = status === "FINALIZED" ? MOCK_VOTING_RESULTS : null;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <Toaster theme="light" />
      <div className="max-w-6xl mx-auto">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-black/50 hover:text-black mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to dashboard
        </Link>

        {/* State switcher */}
        <div className="mb-6 flex flex-wrap gap-2 rounded-xl border border-dashed border-border bg-card p-3">
          <span className="text-xs text-muted-foreground self-center mr-1">Preview:</span>
          {PREVIEW_STATES.map((s) => (
            <button
              key={s}
              onClick={() => { setSearchParams({ preview: s }); }}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                s === preview
                  ? "bg-brand text-white"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-black">{trip.title}</h1>
            <p className="text-black/50 text-sm mt-1">{trip.destination ?? "Destination: surprise me"}</p>
          </div>
        </div>

        <Tabs defaultValue="overview">
          <TabsList variant="line" className="mb-6">
            {(["overview", "participants", "itineraries", "voting"] as const).map((tab) => (
              <TabsTrigger key={tab} value={tab} className="capitalize">
                {tab}
                {tab === "participants" && <span className="ml-1.5 text-xs text-black/40">({MOCK_PARTICIPANTS.length})</span>}
                {tab === "itineraries" && <span className="ml-1.5 text-xs text-black/40">({itineraries.length})</span>}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview">
            <div className="rounded-xl border border-border bg-card p-6">
              <TripOverviewSection trip={trip} itineraries={itineraries} onRefetch={() => { /* no-op */ }} />
            </div>
          </TabsContent>
          <TabsContent value="participants">
            <div className="rounded-xl border border-border bg-card p-6">
              <ParticipantsSection participants={MOCK_PARTICIPANTS} />
            </div>
          </TabsContent>
          <TabsContent value="itineraries">
            <div className="rounded-xl border border-border bg-card p-6">
              <ItinerariesSection
                itineraries={itineraries}
                votingResults={votingResults}
                winnerId={trip.winner_itinerary_id ?? null}
              />
            </div>
          </TabsContent>
          <TabsContent value="voting">
            <div className="rounded-xl border border-border bg-card p-6">
              <VotingSection votingResults={votingResults} itineraries={itineraries} />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
// ---------------------------------------------------------------------------

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

function TripDetailPageInner({ id }: { id: number }) {
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

            <Tabs defaultValue="overview">
              <TabsList variant="line" className="mb-6">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="participants">
                  Participants
                  <span className="ml-1.5 text-xs text-black/40">
                    ({participants.length})
                  </span>
                </TabsTrigger>
                <TabsTrigger value="itineraries">
                  Itineraries
                  <span className="ml-1.5 text-xs text-black/40">
                    ({itineraries.length})
                  </span>
                </TabsTrigger>
                <TabsTrigger value="voting">Voting</TabsTrigger>
              </TabsList>

              <TabsContent value="overview">
                <div className="rounded-xl border border-border bg-card p-6">
                  <TripOverviewSection
                    trip={trip}
                    itineraries={itineraries}
                    onRefetch={refetch}
                  />
                </div>
              </TabsContent>

              <TabsContent value="participants">
                <div className="rounded-xl border border-border bg-card p-6">
                  <ParticipantsSection participants={participants} />
                </div>
              </TabsContent>

              <TabsContent value="itineraries">
                <div className="rounded-xl border border-border bg-card p-6">
                  <ItinerariesSection
                    itineraries={itineraries}
                    votingResults={votingResults}
                    winnerId={trip.winner_itinerary_id ?? null}
                  />
                </div>
              </TabsContent>

              <TabsContent value="voting">
                <div className="rounded-xl border border-border bg-card p-6">
                  <VotingSection
                    votingResults={votingResults}
                    itineraries={itineraries}
                  />
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}
      </div>
    </div>
  );
}

export default function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const preview = searchParams.get("preview") as PreviewState | null;
  const id = parseInt(tripId ?? "0", 10);

  if (preview && (PREVIEW_STATES as readonly string[]).includes(preview)) {
    return <TripDetailPreview preview={preview} setSearchParams={setSearchParams} />;
  }

  return <TripDetailPageInner id={id} />;
}
