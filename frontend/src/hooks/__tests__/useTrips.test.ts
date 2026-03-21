import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useTrips } from "../useTrips";

vi.mock("@/lib/api", () => ({
  trips: {
    list: vi.fn(),
  },
}));

import * as apiModule from "@/lib/api";
const mockList = vi.mocked(apiModule.trips.list);

const FAKE_TRIPS = [
  {
    id: 1,
    trip_code: "ABCD1234",
    title: "Summer Trip",
    destination: null,
    status: "CREATED" as const,
    participant_count: 2,
    preferences_submitted_count: 0,
    created_at: "2024-01-01",
  },
];

describe("useTrips", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("fetches trips on mount and populates the list", async () => {
    mockList.mockResolvedValue(FAKE_TRIPS);

    const { result } = renderHook(() => useTrips());
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.trips).toEqual(FAKE_TRIPS);
    expect(result.current.error).toBeNull();
  });

  it("sets error when fetch fails", async () => {
    mockList.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useTrips());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Network error");
    expect(result.current.trips).toEqual([]);
  });

  it("refetch() triggers a new fetch", async () => {
    mockList.mockResolvedValue(FAKE_TRIPS);

    const { result } = renderHook(() => useTrips());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockList).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refetch();
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockList).toHaveBeenCalledTimes(2);
  });
});
