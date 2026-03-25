import { ItineraryCard } from "@/components/shared/ItineraryCard";
import type { Itinerary, VotingResults } from "@/types";

interface ItinerariesSectionProps {
  itineraries: Itinerary[];
  votingResults: VotingResults | null;
  winnerId: number | null;
}

export function ItinerariesSection({
  itineraries,
  votingResults,
  winnerId,
}: ItinerariesSectionProps) {
  if (itineraries.length === 0) {
    return (
      <p className="text-sm text-black/40 py-4 text-center">
        No itineraries generated yet.
      </p>
    );
  }

  // Build vote count map from last round of results
  const voteCountMap: Record<number, number> = {};
  if (votingResults && votingResults.rounds.length > 0) {
    const lastRound = votingResults.rounds[votingResults.rounds.length - 1];
    Object.entries(lastRound.results).forEach(([id, count]) => {
      voteCountMap[parseInt(id, 10)] = count;
    });
  }

  // Group by iteration
  const byIteration = itineraries.reduce<Record<number, Itinerary[]>>(
    (acc, it) => {
      acc[it.iteration_number] = acc[it.iteration_number] ?? [];
      acc[it.iteration_number].push(it);
      return acc;
    },
    {}
  );

  return (
    <div className="space-y-6">
      {Object.entries(byIteration)
        .sort(([a], [b]) => parseInt(b, 10) - parseInt(a, 10))
        .map(([iter, items]) => (
          <div key={iter}>
            <h3 className="text-xs text-black/40 uppercase tracking-wide mb-3">
              Iteration {iter}
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {[...items]
                .sort((a, b) => {
                  if (a.id === winnerId) return -1;
                  if (b.id === winnerId) return 1;
                  return 0;
                })
                .map((it, index) => (
                  <ItineraryCard
                    key={it.id}
                    itinerary={it}
                    voteCount={voteCountMap[it.id]}
                    isWinner={it.id === winnerId}
                    isGreyedOut={winnerId !== null && it.id !== winnerId}
                    imageIndex={index}
                    totalImages={items.length}
                  />
                ))}
            </div>
          </div>
        ))}
    </div>
  );
}
