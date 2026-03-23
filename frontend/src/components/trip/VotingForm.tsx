import { useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { votes as votesApi, ApiError } from "@/lib/api";
import { ItineraryCard } from "@/components/shared/ItineraryCard";
import { SortableRankItem } from "./SortableRankItem";
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
  const [orderedIds, setOrderedIds] = useState<number[]>(() =>
    itineraries.map((it) => it.id)
  );
  const [activeId, setActiveId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const itineraryMap = useMemo(
    () => new Map(itineraries.map((it) => [it.id, it])),
    [itineraries]
  );

  // Build vote count map from last round
  const voteCountMap: Record<number, number> = {};
  if (votingResults && votingResults.rounds.length > 0) {
    const lastRound = votingResults.rounds[votingResults.rounds.length - 1];
    Object.entries(lastRound.results).forEach(([id, count]) => {
      voteCountMap[parseInt(id, 10)] = count;
    });
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 150, tolerance: 5 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(Number(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);
    if (over && active.id !== over.id) {
      setOrderedIds((prev) => {
        const oldIndex = prev.indexOf(Number(active.id));
        const newIndex = prev.indexOf(Number(over.id));
        return arrayMove(prev, oldIndex, newIndex);
      });
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await votesApi.submit(tripId, token, orderedIds);
      onSuccess();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to submit vote."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeItinerary = activeId !== null ? itineraryMap.get(activeId) : null;
  const activeRank = activeId !== null ? orderedIds.indexOf(activeId) + 1 : 0;

  return (
    <div className="space-y-6">
      {/* Itinerary detail cards */}
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
            Drag to reorder — top is your #1 choice.
          </p>
        </div>

        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="space-y-3"
        >
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={orderedIds}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {orderedIds.map((id, index) => {
                  const itinerary = itineraryMap.get(id);
                  if (!itinerary) return null;
                  return (
                    <SortableRankItem
                      key={id}
                      itinerary={itinerary}
                      rank={index + 1}
                    />
                  );
                })}
              </div>
            </SortableContext>

            <DragOverlay>
              {activeItinerary ? (
                <SortableRankItem
                  itinerary={activeItinerary}
                  rank={activeRank}
                  isDragging
                />
              ) : null}
            </DragOverlay>
          </DndContext>

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
