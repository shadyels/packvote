import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useTrip } from "../useTrip";
import type { Trip } from "@/types";

vi.mock("@/lib/api", () => ({
  trips: { get: vi.fn() },
}));

import * as apiModule from "@/lib/api";
const mockGet = vi.mocked(apiModule.trips.get);

function makeTrip(id = 1): Trip {
  return {
    id,
    trip_code: "ABCD1234",
    creator_id: 99,
    title: "Test Trip",
    destination: null,
    proposed_start_date: null,
    proposed_end_date: null,
    num_options: 3,
    status: "COLLECTING_PREFERENCES",
    current_iteration: 1,
    max_iterations: 10,
    winner_itinerary_id: null,
    generation_error: null,
    created_at: "2024-01-01",
  };
}

describe("useTrip", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("fetches trip on mount and returns data", async () => {
    const trip = makeTrip();
    mockGet.mockResolvedValue(trip);

    const { result } = renderHook(() => useTrip(1));
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.trip).toEqual(trip);
    expect(result.current.error).toBeNull();
    expect(mockGet).toHaveBeenCalledWith(1);
  });

  it("does nothing when tripId is null", () => {
    const { result } = renderHook(() => useTrip(null));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.trip).toBeNull();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("sets error when fetch fails", async () => {
    mockGet.mockRejectedValue(new Error("Not found"));

    const { result } = renderHook(() => useTrip(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Not found");
    expect(result.current.trip).toBeNull();
  });

  it("refetch() triggers a new fetch", async () => {
    const trip = makeTrip();
    mockGet.mockResolvedValue(trip);

    const { result } = renderHook(() => useTrip(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockGet).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refetch();
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockGet).toHaveBeenCalledTimes(2);
  });

  it("fetches with the correct tripId when it changes", async () => {
    mockGet.mockResolvedValue(makeTrip(1));

    const { result, rerender } = renderHook(
      ({ id }: { id: number | null }) => useTrip(id),
      { initialProps: { id: 1 } }
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockGet).toHaveBeenCalledWith(1);

    mockGet.mockResolvedValue(makeTrip(2));
    rerender({ id: 2 });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockGet).toHaveBeenCalledWith(2);
  });
});
