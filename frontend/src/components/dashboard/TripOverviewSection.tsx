import { useState } from "react";
import { Loader2, Zap, RotateCcw, Trophy } from "lucide-react";
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
  VOTING: "Voting",
  ITERATING: "Iterating",
  FINALIZED: "Finalized",
};

const STATUS_BADGE: Record<TripStatus, string> = {
  CREATED: "bg-zinc-700 text-zinc-200 hover:bg-zinc-700",
  COLLECTING_PREFERENCES: "bg-blue-900/60 text-blue-300 hover:bg-blue-900/60",
  GENERATING: "bg-amber-900/60 text-amber-300 hover:bg-amber-900/60",
  VOTING: "bg-accent/20 text-accent hover:bg-accent/20",
  ITERATING: "bg-purple-900/60 text-purple-300 hover:bg-purple-900/60",
  FINALIZED: "bg-green-900/60 text-green-300 hover:bg-green-900/60",
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
          <p className="text-xs text-cream/40 uppercase tracking-wide mb-1">Status</p>
          <Badge className={STATUS_BADGE[trip.status]}>
            {STATUS_LABELS[trip.status]}
          </Badge>
        </div>
        <div>
          <p className="text-xs text-cream/40 uppercase tracking-wide mb-1">Trip Code</p>
          <p className="text-cream font-mono text-sm">{trip.trip_code}</p>
        </div>
        <div>
          <p className="text-xs text-cream/40 uppercase tracking-wide mb-1">PIN</p>
          <p className="text-cream font-mono text-sm">{trip.pin}</p>
        </div>
        {trip.destination && (
          <div>
            <p className="text-xs text-cream/40 uppercase tracking-wide mb-1">Destination</p>
            <p className="text-cream text-sm">{trip.destination}</p>
          </div>
        )}
        {(trip.proposed_start_date || trip.proposed_end_date) && (
          <div>
            <p className="text-xs text-cream/40 uppercase tracking-wide mb-1">Dates</p>
            <p className="text-cream text-sm">
              {trip.proposed_start_date ?? "?"} → {trip.proposed_end_date ?? "?"}
            </p>
          </div>
        )}
        <div>
          <p className="text-xs text-cream/40 uppercase tracking-wide mb-1">Iteration</p>
          <p className="text-cream text-sm">
            {trip.current_iteration} / {trip.max_iterations}
          </p>
        </div>
      </div>

      <Separator className="bg-border" />

      {/* Status-dependent actions */}
      {(trip.status === "CREATED" ||
        trip.status === "COLLECTING_PREFERENCES") && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-cream/70">Actions</h3>
          <Button
            onClick={handleGenerate}
            disabled={isActing}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            {isActing ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Zap className="w-4 h-4 mr-2" />
            )}
            Generate Itineraries
          </Button>
          <p className="text-xs text-cream/40">
            You can trigger generation before all participants have responded.
          </p>
        </div>
      )}

      {trip.status === "GENERATING" && (
        <div className="flex items-center gap-3 text-amber-300">
          <Loader2 className="w-5 h-5 animate-spin" />
          <div>
            <p className="text-sm font-medium">Generating itineraries…</p>
            <p className="text-xs text-amber-300/60">
              This page will update automatically when ready.
            </p>
          </div>
        </div>
      )}

      {(trip.status === "VOTING" || trip.status === "ITERATING") && (
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-cream/70">Actions</h3>

          {/* Pick winner */}
          <div className="space-y-2">
            <p className="text-xs text-cream/50">Manually pick winner</p>
            <div className="flex gap-2">
              <Select
                value={pickWinnerId}
                onValueChange={(v) => {
                  if (v !== null) setPickWinnerId(v);
                }}
              >
                <SelectTrigger className="bg-background border-border text-cream w-64">
                  <SelectValue placeholder="Choose itinerary…" />
                </SelectTrigger>
                <SelectContent className="bg-card border-border text-cream">
                  {currentIterationItineraries.map((it) => (
                    <SelectItem key={it.id} value={String(it.id)}>
                      {it.destination_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                onClick={handlePickWinner}
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
                onClick={handleNewIteration}
                disabled={isActing}
                className="text-cream/60 hover:text-cream border border-border hover:bg-muted/20"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Start new iteration
              </Button>
              <p className="text-xs text-cream/30">
                Iteration {trip.current_iteration + 1} of {trip.max_iterations} max
              </p>
            </div>
          )}
        </div>
      )}

      {trip.status === "FINALIZED" && (
        <div className="rounded-lg border border-green-500/30 bg-green-950/10 p-4">
          <p className="text-green-300 font-medium">🏆 Trip finalized</p>
          <p className="text-xs text-green-300/60 mt-1">
            The group has a winner. Check the Itineraries tab to view it.
          </p>
        </div>
      )}

      {/* Admin vote form — shown during VOTING for current iteration */}
      {trip.status === "VOTING" && currentIterationItineraries.length > 0 && (
        <>
          <Separator className="bg-border" />
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-cream/70">Your vote</h3>
            <p className="text-xs text-cream/40">
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
                    <SelectTrigger className="bg-background border-border text-cream w-16 shrink-0">
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                    <SelectContent className="bg-card border-border text-cream">
                      {currentIterationItineraries.map((_, i) => (
                        <SelectItem key={i + 1} value={String(i + 1)}>
                          {i + 1}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="text-sm text-cream">{it.destination_name}</span>
                </div>
              ))}
            </div>
            <Button
              onClick={handleAdminVote}
              disabled={isActing}
              className="bg-accent hover:bg-accent-hover text-white"
            >
              Submit vote
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
