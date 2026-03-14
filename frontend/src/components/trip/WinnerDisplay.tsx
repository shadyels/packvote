import { ItineraryCard } from "@/components/shared/ItineraryCard";
import type { Itinerary } from "@/types";

interface WinnerDisplayProps {
  winner: Itinerary;
}

export function WinnerDisplay({ winner }: WinnerDisplayProps) {
  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-green-400/50 bg-green-50 px-4 py-3">
        <p className="text-green-800 font-semibold text-sm">
          🏆 Your group has a winner!
        </p>
        <p className="text-xs text-green-700/70 mt-0.5">
          The ranked-choice vote is in. Here's where you're headed.
        </p>
      </div>
      <ItineraryCard itinerary={winner} isWinner={true} />
    </div>
  );
}
