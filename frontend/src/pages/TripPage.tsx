import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useTripView } from "@/hooks/useTripView";
import { TripHeader } from "@/components/trip/TripHeader";
import { ParticipantProgress } from "@/components/trip/ParticipantProgress";
import { PreferenceForm } from "@/components/trip/PreferenceForm";
import { WaitingScreen } from "@/components/trip/WaitingScreen";
import { GeneratingScreen } from "@/components/trip/GeneratingScreen";
import { VotingForm } from "@/components/trip/VotingForm";
import { WinnerDisplay } from "@/components/trip/WinnerDisplay";
import type { ParticipantTripView, TripStatus } from "@/types";

// ---------------------------------------------------------------------------
// Preview mock data — only used when ?preview=<state> is in the URL
// ---------------------------------------------------------------------------
const MOCK_ITINERARIES = [
  {
    id: 1, trip_id: 0, iteration_number: 1,
    destination_name: "Lisbon, Portugal",
    destination_description: "A sun-drenched capital full of pastel trams, hilltop viewpoints, and exceptional food.",
    daily_itinerary_json: JSON.stringify([
      { day_number: 1, title: "Arrival & Alfama", estimated_cost: 80, activities: [
        { time: "10:00 AM", title: "Alfama district walk", description: "Explore the oldest neighbourhood.", estimated_cost: 0 },
        { time: "1:00 PM", title: "Lunch at Mercado da Ribeira", description: "Time Out Market — best of Lisbon's food scene.", estimated_cost: 25 },
        { time: "4:00 PM", title: "Belém Tower & pastéis", description: "Iconic tower + custard tarts from the original bakery.", estimated_cost: 15 },
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
    destination_description: "A compact, atmospheric port city known for wine cellars, baroque churches, and the Douro riverfront.",
    daily_itinerary_json: JSON.stringify([
      { day_number: 1, title: "Ribeira & Wine", estimated_cost: 90, activities: [
        { time: "11:00 AM", title: "Livraria Lello bookshop", description: "One of the world's most beautiful bookshops.", estimated_cost: 5 },
        { time: "2:00 PM", title: "Port wine tasting in Vila Nova de Gaia", description: "Cross the bridge for cellar tours and tastings.", estimated_cost: 30 },
        { time: "6:00 PM", title: "Sunset at Miradouro da Serra do Pilar", description: "Best view over the river and the city.", estimated_cost: 0 },
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

const MOCK_PARTICIPANTS = [
  { id: 1, name: "Alex Kim", preferences_submitted: true },
  { id: 2, name: "Jordan Lee", preferences_submitted: true },
  { id: 3, name: "Sam Rivera", preferences_submitted: false },
  { id: 4, name: "Taylor Moss", preferences_submitted: true },
];

function buildMockData(state: string): ParticipantTripView {
  const status = (
    { collecting: "COLLECTING_PREFERENCES", waiting: "COLLECTING_PREFERENCES",
      generating: "GENERATING", voting: "VOTING", finalized: "FINALIZED" }[state]
    ?? "COLLECTING_PREFERENCES"
  ) as TripStatus;

  return {
    participant: { id: 1, trip_id: 0, email: "you@example.com", name: "Alex Kim",
      preferences_submitted: state === "waiting", created_at: "2026-03-01T10:00:00Z" },
    trip: { id: 0, title: "Spring Group Trip 2026", destination: "Lisbon, Portugal",
      proposed_start_date: "2026-05-10", proposed_end_date: "2026-05-17",
      status, num_options: 2, current_iteration: 1, winner_itinerary_id: status === "FINALIZED" ? 1 : null },
    participants: MOCK_PARTICIPANTS,
    itineraries: status === "VOTING" || status === "FINALIZED" ? MOCK_ITINERARIES : [],
    voting_results: status === "VOTING" ? {
      trip_id: 0, iteration_number: 1,
      rounds: [{ round_number: 1, results: { 1: 3, 2: 1 }, eliminated_option_id: null, winner_id: null }],
      winner_id: null, is_complete: false,
    } : null,
    has_voted: false,
  };
}

const PREVIEW_STATES = ["collecting", "waiting", "generating", "voting", "finalized"] as const;
type PreviewState = typeof PREVIEW_STATES[number];

export default function TripPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const preview = searchParams.get("preview") as PreviewState | null;

  // Preview mode — render all states with mock data, no backend needed
  if (preview && PREVIEW_STATES.includes(preview as PreviewState)) {
    const data = buildMockData(preview);
    const { trip, participant, participants, itineraries, voting_results, has_voted } = data;
    const winner = trip.winner_itinerary_id
      ? itineraries.find((it) => it.id === trip.winner_itinerary_id) ?? null
      : null;
    return (
      <main className="min-h-screen bg-background px-4 py-8">
        {/* State switcher bar */}
        <div className="max-w-2xl mx-auto mb-6 flex flex-wrap gap-2 rounded-xl border border-dashed border-border bg-card p-3">
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
        <div className="max-w-2xl mx-auto space-y-6">
          <TripHeader trip={trip} />
          <ParticipantProgress participants={participants} />
          {(trip.status === "CREATED" || trip.status === "COLLECTING_PREFERENCES") &&
            (participant.preferences_submitted
              ? <WaitingScreen participants={participants} />
              : <PreferenceForm token="preview" onSuccess={() => { setSearchParams({ preview: "waiting" }); }} />
            )}
          {trip.status === "GENERATING" && <GeneratingScreen />}
          {(trip.status === "VOTING" || trip.status === "ITERATING") && (
            <VotingForm tripId={trip.id} token="preview" itineraries={itineraries}
              votingResults={voting_results} hasVoted={has_voted}
              winnerId={trip.winner_itinerary_id} onSuccess={() => { /* no-op in preview */ }} />
          )}
          {trip.status === "FINALIZED" && winner && <WinnerDisplay winner={winner} />}
        </div>
      </main>
    );
  }

  if (!token) {
    return (
      <main className="min-h-screen bg-background px-4 py-8 max-w-2xl mx-auto">
        <p className="text-muted-foreground">Invalid trip link.</p>
      </main>
    );
  }

  return <TripPageInner token={token} navigate={navigate} />;
}

function TripPageInner({
  token,
  navigate,
}: {
  token: string;
  navigate: ReturnType<typeof useNavigate>;
}) {
  const { data, isLoading, error, refetch } = useTripView(token);

  if (isLoading) {
    return (
      <main className="min-h-screen bg-background px-4 py-8 max-w-2xl mx-auto space-y-4">
        <div className="h-7 w-48 rounded bg-muted animate-pulse" />
        <div className="h-4 w-32 rounded bg-muted animate-pulse" />
        <div className="h-24 rounded-lg bg-muted animate-pulse" />
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-background px-4 py-8 max-w-2xl mx-auto">
        <p className="text-red-600 text-sm">{error}</p>
        <button
          onClick={() => {
            navigate("/join");
          }}
          className="mt-4 text-sm text-brand underline"
        >
          Back to join page
        </button>
      </main>
    );
  }

  if (!data) return null;

  const { trip, participant, participants, itineraries, voting_results, has_voted } =
    data;

  const winner = trip.winner_itinerary_id
    ? itineraries.find((it) => it.id === trip.winner_itinerary_id) ?? null
    : null;

  return (
    <main className="min-h-screen bg-background px-4 py-8">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <TripHeader trip={trip} />

        {/* Participant progress (always visible) */}
        <ParticipantProgress participants={participants} />

        {/* Status-dependent body */}
        {(trip.status === "CREATED" ||
          trip.status === "COLLECTING_PREFERENCES") &&
          (participant.preferences_submitted ? (
            <WaitingScreen participants={participants} />
          ) : (
            <PreferenceForm token={token} onSuccess={refetch} />
          ))}

        {trip.status === "GENERATING" && <GeneratingScreen />}

        {(trip.status === "VOTING" || trip.status === "ITERATING") && (
          <VotingForm
            tripId={trip.id}
            token={token}
            itineraries={itineraries}
            votingResults={voting_results}
            hasVoted={has_voted}
            winnerId={trip.winner_itinerary_id}
            onSuccess={refetch}
          />
        )}

        {trip.status === "FINALIZED" && winner && (
          <WinnerDisplay winner={winner} />
        )}

        {trip.status === "FINALIZED" && !winner && itineraries.length > 0 && (
          <div className="space-y-4">
            <p className="text-sm font-medium text-foreground">
              Trip finalized — itinerary options:
            </p>
            <VotingForm
              tripId={trip.id}
              token={token}
              itineraries={itineraries}
              votingResults={voting_results}
              hasVoted={has_voted}
              winnerId={null}
              onSuccess={refetch}
            />
          </div>
        )}
      </div>
    </main>
  );
}
