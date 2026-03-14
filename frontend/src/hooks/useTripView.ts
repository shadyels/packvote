import { useState, useEffect, useCallback, useRef } from "react";
import { participants as participantsApi } from "@/lib/api";
import type { ParticipantTripView } from "@/types";

const POLL_INTERVAL_MS = 5000;

interface UseTripViewResult {
  data: ParticipantTripView | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTripView(token: string): UseTripViewResult {
  const [data, setData] = useState<ParticipantTripView | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refetch = useCallback(() => {
    setTick((t) => t + 1);
  }, []);

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

    participantsApi
      .getTripView(token)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setIsLoading(false);

        // Poll while GENERATING so the page updates automatically
        if (result.trip.status === "GENERATING") {
          pollingRef.current = setInterval(() => {
            participantsApi
              .getTripView(token)
              .then((updated) => {
                if (cancelled) return;
                if (updated.trip.status !== "GENERATING") {
                  stopPolling();
                  setData(updated);
                } else {
                  setData(updated);
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
  }, [token, tick, stopPolling]);

  return { data, isLoading, error, refetch };
}
