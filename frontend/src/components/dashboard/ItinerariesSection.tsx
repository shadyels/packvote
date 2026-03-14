import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import type { Itinerary, DayItinerary, VotingResults } from "@/types";

interface ItinerariesSectionProps {
  itineraries: Itinerary[];
  votingResults: VotingResults | null;
  winnerId: number | null;
}

function parseJson<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json) as T;
  } catch {
    return fallback;
  }
}

function ItineraryCard({
  itinerary,
  voteCount,
  isWinner,
}: {
  itinerary: Itinerary;
  voteCount?: number;
  isWinner: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const highlights = parseJson<string[]>(itinerary.highlights, []);
  const days = parseJson<DayItinerary[]>(itinerary.daily_itinerary_json, []);

  return (
    <Card
      className={`border ${isWinner ? "border-green-500/50 bg-green-50" : "border-border bg-white"}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-black text-base flex items-center gap-2">
              {itinerary.destination_name}
              {isWinner && (
                <Badge className="bg-green-100 text-green-700 text-xs hover:bg-green-100">
                  Winner
                </Badge>
              )}
            </CardTitle>
            <p className="text-xs text-black/40 mt-0.5">
              Iteration {itinerary.iteration_number}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-accent font-semibold">
              {itinerary.currency}{" "}
              {itinerary.total_estimated_budget.toLocaleString()}
            </p>
            {voteCount !== undefined && (
              <p className="text-xs text-black/50 mt-0.5">
                {voteCount} vote{voteCount !== 1 ? "s" : ""}
              </p>
            )}
          </div>
        </div>
        <p className="text-sm text-black/60 leading-relaxed">
          {itinerary.destination_description}
        </p>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Match reasoning */}
        <div>
          <p className="text-xs text-black/40 uppercase tracking-wide mb-1">
            Why this fits the group
          </p>
          <p className="text-sm text-black/70">{itinerary.match_reasoning}</p>
        </div>

        {/* Highlights */}
        {highlights.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {highlights.map((h, i) => (
              <span
                key={i}
                className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full"
              >
                {h}
              </span>
            ))}
          </div>
        )}

        {/* AI metadata */}
        <p className="text-xs text-black/30">
          {itinerary.model_used && itinerary.model_used}
          {itinerary.provider && ` · ${itinerary.provider}`}
        </p>

        {/* Expandable daily itinerary */}
        {days.length > 0 && (
          <>
            <Separator className="bg-border" />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setExpanded((e) => !e); }}
              className="text-black/50 hover:text-black hover:bg-transparent px-0 h-auto"
            >
              {expanded ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5 mr-1" /> Hide itinerary
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5 mr-1" /> Show {days.length}{" "}
                  day itinerary
                </>
              )}
            </Button>

            {expanded && (
              <div className="space-y-4 pt-1">
                {days.map((day) => (
                  <div key={day.day_number}>
                    <p className="text-sm font-medium text-black mb-1.5">
                      Day {day.day_number}: {day.title}
                    </p>
                    <div className="space-y-1.5 pl-3 border-l border-border">
                      {day.activities.map((act, i) => (
                        <div key={i}>
                          <p className="text-sm text-black/80">
                            {act.time && (
                              <span className="text-black/40 mr-1.5">
                                {act.time}
                              </span>
                            )}
                            {act.title}
                          </p>
                          <p className="text-xs text-black/50">
                            {act.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
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
              {items.map((it) => (
                <ItineraryCard
                  key={it.id}
                  itinerary={it}
                  voteCount={voteCountMap[it.id]}
                  isWinner={it.id === winnerId}
                />
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}
