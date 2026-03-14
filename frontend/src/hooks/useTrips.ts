import { useState, useEffect, useCallback } from "react";
import { trips as tripsApi } from "@/lib/api";
import type { TripSummary } from "@/types";

interface UseTripsResult {
  trips: TripSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTrips(): UseTripsResult {
  const [tripList, setTripList] = useState<TripSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    tripsApi
      .list()
      .then((data) => {
        if (!cancelled) {
          setTripList(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load trips");
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tick]);

  return { trips: tripList, isLoading, error, refetch };
}
