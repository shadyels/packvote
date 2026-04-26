import { useState, useEffect, useCallback } from "react";
import { trips as tripsApi } from "@/lib/api";
import type { InvitedTripSummary } from "@/types";

interface UseInvitedTripsResult {
  trips: InvitedTripSummary[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useInvitedTrips(): UseInvitedTripsResult {
  const [tripList, setTripList] = useState<InvitedTripSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => { setTick((t) => t + 1); }, []);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    tripsApi
      .listInvited()
      .then((data) => {
        if (!cancelled) {
          setTripList(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load invited trips");
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tick]);

  return { trips: tripList, isLoading, error, refetch };
}
