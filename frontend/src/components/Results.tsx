import { Check } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { optionTitle } from "@/components/OptionCard";
import type { Itinerary, VotingResults } from "@/types";

interface ResultsProps {
  results: VotingResults;
  /** Options of the same iteration, for names. */
  options: Itinerary[];
}

export function Results({ results, options }: ResultsProps) {
  const name = (id: number) => {
    const o = options.find((x) => x.id === id);
    return o ? optionTitle(o) : `#${id.toString()}`;
  };

  if (results.rounds.length === 0) {
    return <p className="text-sm text-muted-foreground">No votes recorded yet.</p>;
  }

  return (
    <div className="flex flex-col gap-5">
      {results.winner_id !== null && (
        <p className="flex items-center gap-2 rounded-lg bg-success-subtle px-3 py-2 text-sm font-medium text-success">
          <Check className="size-4" aria-hidden="true" />
          Winner: {name(results.winner_id)}
        </p>
      )}
      {results.rounds.map((round) => {
        const rows = Object.entries(round.results)
          .map(([id, count]) => ({ id: Number(id), count }))
          .sort((a, b) => b.count - a.count);
        const total = rows.reduce((sum, r) => sum + r.count, 0);
        return (
          <section key={round.round_number} aria-label={`Round ${round.round_number.toString()}`}>
            <h4 className="mb-2 text-sm font-semibold">Round {round.round_number}</h4>
            <ul className="flex flex-col gap-2">
              {rows.map((r) => (
                <li key={r.id} className="relative overflow-hidden rounded-lg border px-3 py-2">
                  <div
                    aria-hidden="true"
                    className="absolute inset-y-0 left-0 bg-muted"
                    style={{ width: `${total ? ((r.count / total) * 100).toString() : "0"}%` }}
                  />
                  <div className="relative flex items-center justify-between gap-3 text-sm">
                    <span className="min-w-0 truncate">{name(r.id)}</span>
                    <span className="flex shrink-0 items-center gap-2">
                      {round.eliminated_option_id === r.id && (
                        <Badge tone="danger">Eliminated</Badge>
                      )}
                      {round.winner_id === r.id && <Badge tone="success">Winner</Badge>}
                      <span className="font-medium tabular-nums">{r.count}</span>
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
