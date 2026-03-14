import { useState, useEffect } from "react";
import { trips } from "@/lib/api";
import type { Trip } from "@/types";

interface UseTripResult {
  trip: Trip | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTrip(tripId: number | null): UseTripResult {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (tripId === null) return;

    setIsLoading(true);
    setError(null);

    trips
      .get(tripId)
      .then((data) => {
        setTrip(data);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load trip");
        setIsLoading(false);
      });
  }, [tripId, tick]);

  return { trip, isLoading, error, refetch: () => { setTick((t) => t + 1); } };
}
