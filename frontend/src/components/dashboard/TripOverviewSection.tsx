import { useState } from "react";
import { Loader2, Zap, RotateCcw, Trophy, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { trips as tripsApi, votes as votesApi, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Trip, Itinerary, TripStatus } from "@/types";

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
  onRefetch: () => void;
}

export function TripOverviewSection({
  trip,
  itineraries,
  onRefetch,
}: TripOverviewSectionProps) {
  const [isActing, setIsActing] = useState(false);
  const [adminRankings, setAdminRankings] = useState<Record<number, string>>(
    {}
  );
  const [pickWinnerId, setPickWinnerId] = useState<string>("");

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

  const handleAdminVote = async () => {
    const itineraryIds = currentIterationItineraries.map((it) => it.id);
    // Build rankings: adminRankings maps itinerary_id -> rank position (1=best)
    // Sort by rank position ascending then map to IDs
    const sorted = itineraryIds
      .filter((id) => adminRankings[id])
      .sort(
        (a, b) =>
          parseInt(adminRankings[a], 10) - parseInt(adminRankings[b], 10)
      );

    if (sorted.length !== itineraryIds.length) {
      toast.error("Please rank all options before submitting.");
      return;
    }

    setIsActing(true);
    try {
      await votesApi.adminVote(trip.id, sorted);
      toast.success("Vote submitted!");
      onRefetch();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to submit vote.");
    } finally {
      setIsActing(false);
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
            </div>
          </div>
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
                      {it.destination_name}
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

      {/* Admin vote form — shown during VOTING for current iteration */}
      {trip.status === "VOTING" && currentIterationItineraries.length > 0 && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-black/70">Your vote</h3>
            <p className="text-xs text-black/40">
              Rank each option (1 = most preferred).
            </p>
            <div className="space-y-2">
              {currentIterationItineraries.map((it) => (
                <div key={it.id} className="flex items-center gap-3">
                  <Select
                    value={adminRankings[it.id] ?? ""}
                    onValueChange={(v) => {
                      if (v !== null)
                        setAdminRankings((prev) => ({ ...prev, [it.id]: v }));
                    }}
                  >
                    <SelectTrigger className="bg-card border-border text-black w-16 shrink-0">
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                    <SelectContent className="bg-card border-border text-black">
                      {currentIterationItineraries.map((_, i) => (
                        <SelectItem key={i + 1} value={String(i + 1)}>
                          {i + 1}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="text-sm text-black">{it.destination_name}</span>
                </div>
              ))}
            </div>
            <Button
              onClick={() => { void handleAdminVote(); }}
              disabled={isActing}
              className="bg-brand hover:bg-brand-hover text-white"
            >
              Submit vote
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
