import { useState } from "react";
import { votes as votesApi, ApiError } from "@/lib/api";
import { ItineraryCard } from "@/components/shared/ItineraryCard";
import type { Itinerary, VotingResults } from "@/types";

interface VotingFormProps {
  tripId: number;
  token: string;
  itineraries: Itinerary[];
  votingResults: VotingResults | null;
  hasVoted: boolean;
  winnerId: number | null;
  onSuccess: () => void;
}

export function VotingForm({
  tripId,
  token,
  itineraries,
  votingResults,
  hasVoted,
  winnerId,
  onSuccess,
}: VotingFormProps) {
  const [rankings, setRankings] = useState<Record<number, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Build vote count map from last round
  const voteCountMap: Record<number, number> = {};
  if (votingResults && votingResults.rounds.length > 0) {
    const lastRound = votingResults.rounds[votingResults.rounds.length - 1];
    Object.entries(lastRound.results).forEach(([id, count]) => {
      voteCountMap[parseInt(id, 10)] = count;
    });
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const itineraryIds = itineraries.map((it) => it.id);
    const sorted = itineraryIds
      .filter((id) => rankings[id])
      .sort(
        (a, b) => parseInt(rankings[a], 10) - parseInt(rankings[b], 10)
      );

    if (sorted.length !== itineraryIds.length) {
      setError("Please rank all options before submitting.");
      return;
    }

    setIsSubmitting(true);
    try {
      await votesApi.submit(tripId, token, sorted);
      onSuccess();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to submit vote."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Itinerary cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {itineraries.map((it) => (
          <ItineraryCard
            key={it.id}
            itinerary={it}
            voteCount={voteCountMap[it.id]}
            isWinner={it.id === winnerId}
          />
        ))}
      </div>

      {/* Voting form */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">
            {hasVoted ? "Update Your Vote" : "Cast Your Vote"}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Rank each option (1 = most preferred).
          </p>
        </div>

        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="space-y-3"
        >
          {itineraries.map((it) => (
            <div key={it.id} className="flex items-center gap-3">
              <select
                value={rankings[it.id] ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  setRankings((prev) => ({ ...prev, [it.id]: v }));
                }}
                className="w-16 shrink-0 rounded-md border border-border bg-background px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
              >
                <option value="">—</option>
                {itineraries.map((_, i) => (
                  <option key={i + 1} value={String(i + 1)}>
                    {i + 1}
                  </option>
                ))}
              </select>
              <span className="text-sm text-foreground">
                {it.destination_name}
              </span>
            </div>
          ))}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 hover:-translate-y-0.5 hover:bg-brand-hover hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed disabled:translate-y-0"
          >
            {isSubmitting
              ? "Submitting…"
              : hasVoted
                ? "Update Vote"
                : "Submit Vote"}
          </button>
        </form>
      </div>
    </div>
  );
}
