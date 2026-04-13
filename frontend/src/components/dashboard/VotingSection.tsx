import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { Itinerary, VotingResults } from "@/types";

interface VotingSectionProps {
  votingResults: VotingResults | null;
  itineraries: Itinerary[];
}

function itineraryName(id: number, itineraries: Itinerary[]): string {
  const it = itineraries.find((i) => i.id === id);
  return it?.option_title ?? it?.destination_name ?? `#${id.toString()}`;
}

export function VotingSection({
  votingResults,
  itineraries,
}: VotingSectionProps) {
  if (!votingResults || votingResults.rounds.length === 0) {
    return (
      <p className="text-sm text-black/40 py-4 text-center">
        No votes recorded yet.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {votingResults.winner_id && (
        <div className="rounded-lg border border-green-500/30 bg-green-50 p-4">
          <p className="text-sm text-green-700">
            🏆 Winner:{" "}
            <span className="font-semibold">
              {itineraryName(votingResults.winner_id, itineraries)}
            </span>
          </p>
        </div>
      )}

      <div className="space-y-4">
        <h3 className="text-xs text-black/40 uppercase tracking-wide">
          Iteration {votingResults.iteration_number} · Rounds
        </h3>

        {votingResults.rounds.map((round) => (
          <div key={round.round_number} className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-black/50">
                Round {round.round_number}
              </span>
              {round.eliminated_option_id && (
                <Badge className="bg-red-100 text-red-700 text-xs hover:bg-red-100">
                  Eliminated:{" "}
                  {itineraryName(round.eliminated_option_id, itineraries)}
                </Badge>
              )}
              {round.winner_id && (
                <Badge className="bg-green-100 text-green-700 text-xs hover:bg-green-100">
                  ✓ {itineraryName(round.winner_id, itineraries)}
                </Badge>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-black/50">Option</TableHead>
                  <TableHead className="text-black/50 text-right">
                    Votes
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(round.results)
                  .sort(([, a], [, b]) => b - a)
                  .map(([idStr, count]) => {
                    const id = parseInt(idStr, 10);
                    const isEliminated = id === round.eliminated_option_id;
                    const isWinner = id === round.winner_id;
                    return (
                      <TableRow
                        key={id}
                        className={`border-border ${isEliminated ? "opacity-40" : "hover:bg-muted/20"}`}
                      >
                        <TableCell
                          className={`text-sm ${isWinner ? "text-green-700 font-medium" : "text-black"}`}
                        >
                          {itineraryName(id, itineraries)}
                        </TableCell>
                        <TableCell className="text-right text-black/70 text-sm">
                          {count}
                        </TableCell>
                      </TableRow>
                    );
                  })}
              </TableBody>
            </Table>
          </div>
        ))}
      </div>
    </div>
  );
}
