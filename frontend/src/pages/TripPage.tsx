import { useParams, useNavigate } from "react-router-dom";
import { useTripView } from "@/hooks/useTripView";
import { TripHeader } from "@/components/trip/TripHeader";
import { ParticipantProgress } from "@/components/trip/ParticipantProgress";
import { PreferenceForm } from "@/components/trip/PreferenceForm";
import { WaitingScreen } from "@/components/trip/WaitingScreen";
import { GeneratingScreen } from "@/components/trip/GeneratingScreen";
import { AlertTriangle } from "lucide-react";
import { VotingForm } from "@/components/trip/VotingForm";
import { WinnerDisplay } from "@/components/trip/WinnerDisplay";

export default function TripPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

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

        {trip.status === "GENERATION_FAILED" && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6 flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-700">
                Itinerary generation encountered an issue
              </p>
              <p className="text-xs text-red-600/70 mt-1">
                The trip organizer has been notified and can retry. Check back soon.
              </p>
            </div>
          </div>
        )}

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
