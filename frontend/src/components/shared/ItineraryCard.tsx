import { useState } from "react";
import { Trophy } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { parseJson } from "@/lib/utils";
import { useDestinationImage } from "@/lib/unsplash";
import type { Itinerary, DayItinerary } from "@/types";
import { DayDetailDrawer } from "./DayDetailDrawer";

const VISIBLE_DAY_LIMIT = 5;

interface ItineraryCardProps {
  itinerary: Itinerary;
  voteCount?: number;
  isWinner: boolean;
  isGreyedOut?: boolean;
  imageIndex?: number;
  totalImages?: number;
}

function DestinationImage({
  destination,
  imageIndex = 0,
  totalImages = 1,
}: {
  destination: string;
  imageIndex?: number;
  totalImages?: number;
}) {
  const { imageUrl, gradient, isLoading } = useDestinationImage(
    destination,
    imageIndex,
    totalImages
  );

  if (isLoading) {
    return (
      <div className="h-44 w-full animate-shimmer rounded-t-xl" />
    );
  }

  return (
    <div className="relative h-44 w-full overflow-hidden rounded-t-xl">
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={destination}
          className="h-full w-full object-cover"
        />
      ) : (
        <div className="h-full w-full" style={{ background: gradient }} />
      )}
      {/* Destination name overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
    </div>
  );
}

export function ItineraryCard({
  itinerary,
  voteCount,
  isWinner,
  isGreyedOut = false,
  imageIndex = 0,
  totalImages = 1,
}: ItineraryCardProps) {
  const [selectedDayIndex, setSelectedDayIndex] = useState<number | null>(null);
  const [showAllDays, setShowAllDays] = useState(false);

  const highlights = parseJson<string[]>(itinerary.highlights, []);
  const days = parseJson<DayItinerary[]>(itinerary.daily_itinerary_json, []);
  const visibleDays = showAllDays ? days : days.slice(0, VISIBLE_DAY_LIMIT);

  return (
    <Card
      className={`overflow-hidden border pt-0 ${
        isWinner
          ? "border-green-400/60 shadow-[0_0_0_1px_rgba(74,222,128,0.3),0_4px_20px_rgba(74,222,128,0.12)]"
          : "border-border bg-card"
      } ${isGreyedOut ? "opacity-50 grayscale" : ""}`}
    >
      {/* Image header */}
      <DestinationImage
        destination={itinerary.destination_name}
        imageIndex={imageIndex}
        totalImages={totalImages}
      />

      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-black text-base flex items-center gap-2">
              {itinerary.destination_name}
              {isWinner && (
                <Badge className="bg-green-100 text-green-700 text-xs hover:bg-green-100 flex items-center gap-1">
                  <Trophy className="h-3 w-3" />
                  Winner
                </Badge>
              )}
            </CardTitle>
            <p className="text-xs text-black/40 mt-0.5">
              Iteration {itinerary.iteration_number}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-brand font-semibold">
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
                className="text-xs bg-brand/10 text-brand px-2 py-0.5 rounded-full"
              >
                {h}
              </span>
            ))}
          </div>
        )}

        {/* Hybrid day overview */}
        {days.length > 0 && (
          <>
            <Separator className="bg-border" />
            <div className="space-y-1.5">
              {visibleDays.map((day, idx) => (
                <button
                  key={day.day_number}
                  onClick={() => {
                    setSelectedDayIndex(idx);
                  }}
                  className="w-full text-left rounded-lg px-3 py-2 transition-colors hover:bg-accent/50 border-l-2 border-border hover:border-brand/50"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">
                      Day {day.day_number} · {day.title}
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0 ml-2" aria-label={`${String(day.activities.length)} activities`}>
                      {day.activities.length}
                    </span>
                  </div>
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    {day.activities.map((act, i) => (
                      <span
                        key={`${String(i)}-${act.time ?? ""}-${act.title}`}
                        className="text-[10px] bg-brand/10 text-brand px-1.5 py-0.5 rounded"
                      >
                        {act.title}
                      </span>
                    ))}
                  </div>
                </button>
              ))}

              {/* Show more / fewer toggle for trips > VISIBLE_DAY_LIMIT days */}
              {days.length > VISIBLE_DAY_LIMIT && (
                <button
                  onClick={() => {
                    setShowAllDays((s) => !s);
                  }}
                  className="w-full text-xs text-muted-foreground hover:text-foreground text-center py-1 transition-colors"
                >
                  {showAllDays
                    ? "Show fewer days ↑"
                    : `Show ${String(days.length - VISIBLE_DAY_LIMIT)} more days ↓`}
                </button>
              )}
            </div>
          </>
        )}
      </CardContent>

      <DayDetailDrawer
        days={days}
        initialDayIndex={selectedDayIndex ?? 0}
        open={selectedDayIndex !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedDayIndex(null);
        }}
        currency={itinerary.currency}
      />
    </Card>
  );
}
