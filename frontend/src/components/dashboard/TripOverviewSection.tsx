import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Zap, RotateCcw, Trophy, AlertTriangle, Trash2, CheckCircle } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { EditTripDialog } from "./EditTripDialog";
import { toast } from "sonner";
import { trips as tripsApi, votes as votesApi, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { SortableRankItem } from "@/components/trip/SortableRankItem";
import type { Trip, Itinerary, Participant, TripStatus } from "@/types";

const STATUS_LABELS: Record<TripStatus, string> = {
  CREATED: "Created",
  COLLECTING_PREFERENCES: "Collecting Preferences",
  GENERATING: "Generating…",
  GENERATION_FAILED: "Generation Failed",
  VOTING: "Voting",
  ITERATING: "Iterating",
  FINALIZED: "Finalized",
};

const STATUS_BADGE: Record<TripStatus, string> = {
  CREATED: "bg-zinc-100 text-zinc-700 hover:bg-zinc-100",
  COLLECTING_PREFERENCES: "bg-blue-100 text-blue-700 hover:bg-blue-100",
  GENERATING: "bg-amber-100 text-amber-700 hover:bg-amber-100",
  GENERATION_FAILED: "bg-red-100 text-red-700 hover:bg-red-100",
  VOTING: "bg-brand/20 text-brand hover:bg-brand/20",
  ITERATING: "bg-purple-100 text-purple-700 hover:bg-purple-100",
  FINALIZED: "bg-green-100 text-green-700 hover:bg-green-100",
};

interface TripOverviewSectionProps {
  trip: Trip;
  itineraries: Itinerary[];
  participants: Participant[];
  onRefetch: () => void;
}

export function TripOverviewSection({
  trip,
  itineraries,
  participants,
  onRefetch,
}: TripOverviewSectionProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const creatorParticipant = user
    ? (participants.find((p) => p.email === user.email) ?? null)
    : null;
  const creatorHasVoted = creatorParticipant?.has_voted_current_iteration ?? false;
  const nonVoterCount = participants.filter((p) => !p.has_voted_current_iteration).length;
  const [isActing, setIsActing] = useState(false);
  const [orderedIds, setOrderedIds] = useState<number[]>(() =>
    itineraries
      .filter((it) => it.iteration_number === trip.current_iteration)
      .map((it) => it.id)
  );
  const [activeId, setActiveId] = useState<number | null>(null);
  const [pickWinnerId, setPickWinnerId] = useState<string>("");
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const currentIterationItineraries = itineraries.filter(
    (it) => it.iteration_number === trip.current_iteration
  );

  const handleGenerate = async () => {
    setIsActing(true);
    try {
      await tripsApi.triggerGeneration(trip.id);
      toast.success("Generation started — itineraries will appear shortly.");
      onRefetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to trigger generation.");
    } finally {
      setIsActing(false);
    }
  };

  const handleNewIteration = async () => {
    setIsActing(true);
    try {
      await tripsApi.triggerNewIteration(trip.id);
      toast.success("New iteration started.");
      onRefetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to start new iteration.");
    } finally {
      setIsActing(false);
    }
  };

  const handlePickWinner = async () => {
    if (!pickWinnerId) return;
    setIsActing(true);
    try {
      await tripsApi.pickWinner(trip.id, parseInt(pickWinnerId, 10));
      toast.success("Winner selected — trip finalized!");
      onRefetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to pick winner.");
    } finally {
      setIsActing(false);
    }
  };

  const itineraryMap = useMemo(
    () => new Map(currentIterationItineraries.map((it) => [it.id, it])),
    [currentIterationItineraries]
  );

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

  const handleAdminVote = async () => {
    setIsActing(true);
    try {
      await votesApi.adminVote(trip.id, orderedIds);
      toast.success("Vote submitted!");
      onRefetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to submit vote.");
    } finally {
      setIsActing(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await tripsApi.delete(trip.id);
      toast.success("Trip deleted.");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to delete trip.");
      setIsDeleteOpen(false);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Trip metadata */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-black/40 uppercase tracking-wide mb-1">Status</p>
          <Badge className={STATUS_BADGE[trip.status]}>
            {STATUS_LABELS[trip.status]}
          </Badge>
        </div>
        <div>
          <p className="text-xs text-black/40 uppercase tracking-wide mb-1">Trip Code</p>
          <p className="text-black font-mono text-sm">{trip.trip_code}</p>
        </div>
{trip.destination && (
          <div>
            <p className="text-xs text-black/40 uppercase tracking-wide mb-1">Destination</p>
            <p className="text-black text-sm">{trip.destination}</p>
          </div>
        )}
        {(trip.proposed_start_date || trip.proposed_end_date) && (
          <div>
            <p className="text-xs text-black/40 uppercase tracking-wide mb-1">Dates</p>
            <p className="text-black text-sm">
              {trip.proposed_start_date ?? "?"} → {trip.proposed_end_date ?? "?"}
            </p>
          </div>
        )}
        <div>
          <p className="text-xs text-black/40 uppercase tracking-wide mb-1">Iteration</p>
          <p className="text-black text-sm">
            {trip.current_iteration} / {trip.max_iterations}
          </p>
        </div>
      </div>

      <Separator className="bg-border" />

      {/* Status-dependent actions */}
      {(trip.status === "CREATED" ||
        trip.status === "COLLECTING_PREFERENCES") && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-black/70">Actions</h3>
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              onClick={() => { void handleGenerate(); }}
              disabled={isActing}
              className="bg-brand hover:bg-brand-hover text-white"
            >
              {isActing ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Zap className="w-4 h-4 mr-2" />
              )}
              Generate Itineraries
            </Button>
            <EditTripDialog trip={trip} onUpdated={onRefetch} />
          </div>
          <p className="text-xs text-black/40">
            You can trigger generation before all participants have responded.
          </p>
        </div>
      )}

      {trip.status === "GENERATING" && (
        <div className="flex items-center gap-3 text-amber-700">
          <Loader2 className="w-5 h-5 animate-spin" />
          <div>
            <p className="text-sm font-medium">Generating itineraries…</p>
            <p className="text-xs text-amber-700/60">
              This page will update automatically when ready.
            </p>
          </div>
        </div>
      )}

      {trip.status === "GENERATION_FAILED" && (
        <div className="space-y-3">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-red-700 font-medium text-sm">Generation failed</p>
              {trip.generation_error && (
                <p className="text-xs text-red-600/80 mt-1 break-words">
                  {trip.generation_error}
                </p>
              )}
              <p className="text-xs text-red-600/60 mt-2">
                You can edit the trip details below before retrying.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              onClick={() => { void handleGenerate(); }}
              disabled={isActing}
              className="bg-brand hover:bg-brand-hover text-white"
            >
              {isActing ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Zap className="w-4 h-4 mr-2" />
              )}
              Retry Generation
            </Button>
            <EditTripDialog trip={trip} onUpdated={onRefetch} />
          </div>
        </div>
      )}

      {(trip.status === "VOTING" || trip.status === "ITERATING") && (
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-black/70">Actions</h3>

          {/* Pick winner */}
          <div className="space-y-2">
            <p className="text-xs text-black/50">Manually pick winner</p>
            <div className="flex gap-2">
              <Select
                value={pickWinnerId}
                onValueChange={(v) => {
                  if (v !== null) setPickWinnerId(v);
                }}
              >
                <SelectTrigger className="bg-card border-border text-black w-64">
                  <SelectValue placeholder="Choose itinerary…" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border text-black">
                  {currentIterationItineraries.map((it) => (
                    <SelectItem key={it.id} value={String(it.id)}>
                      {it.option_title ?? it.destination_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                onClick={() => { void handlePickWinner(); }}
                disabled={!pickWinnerId || isActing}
                className="bg-green-700 hover:bg-green-600 text-white"
              >
                <Trophy className="w-4 h-4 mr-1" />
                Finalize
              </Button>
            </div>
          </div>

          {/* New iteration */}
          {trip.status === "VOTING" && (
            <div className="space-y-1">
              <Button
                variant="ghost"
                onClick={() => { void handleNewIteration(); }}
                disabled={isActing}
                className="text-black/60 hover:text-black border border-border hover:bg-muted/20"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Start new iteration
              </Button>
              <p className="text-xs text-black/30">
                Iteration {trip.current_iteration + 1} of {trip.max_iterations} max
              </p>
            </div>
          )}
        </div>
      )}

      {trip.status === "FINALIZED" && (
        <div className="rounded-lg border border-green-500/30 bg-green-50 p-4 flex items-start gap-3">
          <Trophy className="h-4 w-4 text-green-700 mt-0.5 shrink-0" />
          <div>
          <p className="text-green-700 font-medium">Trip finalized</p>
          <p className="text-xs text-green-700/60 mt-1">
            The group has a winner. Check the Itineraries tab to view it.
          </p>
          </div>
        </div>
      )}

      {/* Danger zone */}
      {trip.status !== "GENERATING" && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-red-600">Danger Zone</h3>
            <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
              <DialogTrigger
                render={
                  <button className="inline-flex items-center gap-2 rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 hover:text-red-700 transition-colors" />
                }
              >
                <Trash2 className="w-4 h-4" />
                Delete Trip
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete &ldquo;{trip.title}&rdquo;?</DialogTitle>
                  <DialogDescription>
                    This will permanently delete this trip, all participants, preferences,
                    itineraries, and voting data. This action cannot be undone.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <DialogClose render={<Button variant="outline" />}>
                    Cancel
                  </DialogClose>
                  <Button
                    onClick={() => { void handleDelete(); }}
                    disabled={isDeleting}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    {isDeleting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    Delete permanently
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <p className="text-xs text-black/30">
              Permanently remove this trip and all associated data.
            </p>
          </div>
        </>
      )}

      {/* Admin vote form — shown during VOTING for current iteration */}
      {trip.status === "VOTING" && currentIterationItineraries.length > 0 && (
        <>
          <Separator className="bg-border" />
          {creatorHasVoted ? (
            <div className="rounded-lg border border-green-500/30 bg-green-50 p-4 flex items-start gap-3">
              <CheckCircle className="h-4 w-4 text-green-700 mt-0.5 shrink-0" />
              <div>
                <p className="text-green-700 font-medium text-sm">Your vote is in</p>
                <p className="text-xs text-green-700/70 mt-1">
                  {nonVoterCount === 0
                    ? "All participants have voted — results coming up."
                    : `Waiting on ${nonVoterCount.toString()} more participant${nonVoterCount === 1 ? "" : "s"}.`}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-medium text-black/70">Your vote</h3>
                <p className="text-xs text-black/40 mt-0.5">
                  Drag to reorder — top is your #1 choice.
                </p>
              </div>
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
                  {(() => {
                    if (activeId === null) return null;
                    const active = itineraryMap.get(activeId);
                    if (!active) return null;
                    return (
                      <SortableRankItem
                        itinerary={active}
                        rank={orderedIds.indexOf(activeId) + 1}
                        isDragging
                      />
                    );
                  })()}
                </DragOverlay>
              </DndContext>
              <Button
                onClick={() => { void handleAdminVote(); }}
                disabled={isActing}
                className="bg-brand hover:bg-brand-hover text-white"
              >
                Submit vote
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
