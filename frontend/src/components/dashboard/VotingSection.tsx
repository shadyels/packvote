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
  return itineraries.find((it) => it.id === id)?.destination_name ?? `#${id.toString()}`;
}

export function VotingSection({
  votingResults,
  itineraries,
}: VotingSectionProps) {
  if (!votingResults || votingResults.rounds.length === 0) {
    return (
      <p className="text-sm text-cream/40 py-4 text-center">
        No votes recorded yet.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {votingResults.winner_id && (
        <div className="rounded-lg border border-green-500/30 bg-green-950/10 p-4">
          <p className="text-sm text-green-300">
            🏆 Winner:{" "}
            <span className="font-semibold">
              {itineraryName(votingResults.winner_id, itineraries)}
            </span>
          </p>
        </div>
      )}

      <div className="space-y-4">
        <h3 className="text-xs text-cream/40 uppercase tracking-wide">
          Iteration {votingResults.iteration_number} · Rounds
        </h3>

        {votingResults.rounds.map((round) => (
          <div key={round.round_number} className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-cream/50">
                Round {round.round_number}
              </span>
              {round.eliminated_option_id && (
                <Badge className="bg-red-900/40 text-red-300 text-xs hover:bg-red-900/40">
                  Eliminated:{" "}
                  {itineraryName(round.eliminated_option_id, itineraries)}
                </Badge>
              )}
              {round.winner_id && (
                <Badge className="bg-green-900/40 text-green-300 text-xs hover:bg-green-900/40">
                  ✓ {itineraryName(round.winner_id, itineraries)}
                </Badge>
              )}
            </div>

            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-cream/50">Option</TableHead>
                  <TableHead className="text-cream/50 text-right">
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
                          className={`text-sm ${isWinner ? "text-green-300 font-medium" : "text-cream"}`}
                        >
                          {itineraryName(id, itineraries)}
                        </TableCell>
                        <TableCell className="text-right text-cream/70 text-sm">
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
