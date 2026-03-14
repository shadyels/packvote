import { useState, useEffect, useCallback, useRef } from "react";
import {
  trips as tripsApi,
  participants as participantsApi,
  itineraries as itinerariesApi,
  votes as votesApi,
  aiLogs as aiLogsApi,
} from "@/lib/api";
import type {
  Trip,
  Participant,
  Itinerary,
  VotingResults,
  AICallLog,
  TripStatus,
} from "@/types";

const VOTING_STATUSES: TripStatus[] = ["VOTING", "ITERATING", "FINALIZED"];
const POLL_INTERVAL_MS = 5000;

interface TripDetailData {
  trip: Trip | null;
  participants: Participant[];
  itineraries: Itinerary[];
  votingResults: VotingResults | null;
  aiLogs: AICallLog[];
}

interface UseTripDetailResult extends TripDetailData {
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

async function fetchAll(tripId: number): Promise<TripDetailData> {
  const [tripResult, participantsResult, itinerariesResult, aiLogsResult] =
    await Promise.allSettled([
      tripsApi.get(tripId),
      participantsApi.listByTrip(tripId),
      itinerariesApi.getByTrip(tripId),
      aiLogsApi.getByTrip(tripId),
    ]);

  const trip = tripResult.status === "fulfilled" ? tripResult.value : null;

  let votingResults: VotingResults | null = null;
  if (trip && VOTING_STATUSES.includes(trip.status)) {
    try {
      votingResults = await votesApi.getResults(tripId);
    } catch {
      // Not fatal — voting may not have started yet
    }
  }

  return {
    trip,
    participants:
      participantsResult.status === "fulfilled" ? participantsResult.value : [],
    itineraries:
      itinerariesResult.status === "fulfilled" ? itinerariesResult.value : [],
    votingResults,
    aiLogs: aiLogsResult.status === "fulfilled" ? aiLogsResult.value : [],
  };
}

export function useTripDetail(tripId: number): UseTripDetailResult {
  const [data, setData] = useState<TripDetailData>({
    trip: null,
    participants: [],
    itineraries: [],
    votingResults: null,
    aiLogs: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current !== null) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    stopPolling();

    fetchAll(tripId)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setIsLoading(false);

        // Start polling while GENERATING
        if (result.trip?.status === "GENERATING") {
          pollingRef.current = setInterval(() => {
            tripsApi
              .get(tripId)
              .then((trip) => {
                if (cancelled) return;
                if (trip.status !== "GENERATING") {
                  stopPolling();
                  // Full refetch to get new itineraries and results
                  setTick((t) => t + 1);
                } else {
                  setData((prev) => ({ ...prev, trip }));
                }
              })
              .catch(() => {
                // Silent — will retry on next interval
              });
          }, POLL_INTERVAL_MS);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Failed to load trip data"
        );
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [tripId, tick, stopPolling]);

  return { ...data, isLoading, error, refetch };
}
