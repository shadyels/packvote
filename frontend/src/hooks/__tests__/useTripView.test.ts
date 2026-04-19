import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useTripView } from "../useTripView";
import type { ParticipantTripView } from "@/types";

vi.mock("@/lib/api", () => ({
  participants: {
    getTripView: vi.fn(),
  },
}));

import * as apiModule from "@/lib/api";
const mockGetTripView = vi.mocked(apiModule.participants.getTripView);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTripView(
  status: ParticipantTripView["trip"]["status"] = "COLLECTING_PREFERENCES"
): ParticipantTripView {
  return {
    participant: {
      id: 1,
      trip_id: 1,
      email: "p@test.com",
      name: null,
      preferences_submitted: false,
      has_voted_current_iteration: false,
      created_at: "2024-01-01",
    },
    trip: {
      id: 1,
      title: "Test Trip",
      destination: null,
      proposed_start_date: null,
      proposed_end_date: null,
      status,
      num_options: 3,
      current_iteration: 1,
      winner_itinerary_id: null,
      generation_error: null,
      notes: null,
    },
    participants: [{ id: 1, name: null, email_local: "participant", preferences_submitted: false }],
    itineraries: [],
    voting_results: null,
    has_voted: false,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useTripView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fetches trip view on mount and returns data", async () => {
    const view = makeTripView();
    mockGetTripView.mockResolvedValue(view);

    const { result } = renderHook(() => useTripView("test-token"));
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data).toEqual(view);
    expect(result.current.error).toBeNull();
  });

  it("sets error when fetch fails", async () => {
    mockGetTripView.mockRejectedValue(new Error("Trip not found"));

    const { result } = renderHook(() => useTripView("bad-token"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Trip not found");
    expect(result.current.data).toBeNull();
  });

  it("refetch() triggers a new fetch", async () => {
    const view = makeTripView();
    mockGetTripView.mockResolvedValue(view);

    const { result } = renderHook(() => useTripView("token"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockGetTripView).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refetch();
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockGetTripView).toHaveBeenCalledTimes(2);
  });

  it("starts polling when trip status is GENERATING and stops when status changes", async () => {
    vi.useFakeTimers();
    const generatingView = makeTripView("GENERATING");
    const votingView = makeTripView("VOTING");

    mockGetTripView
      .mockResolvedValueOnce(generatingView) // initial fetch
      .mockResolvedValueOnce(votingView); // poll

    const { result } = renderHook(() => useTripView("token"));

    // Flush only the initial fetch (resolved Promise → microtask queue only, no timers)
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.data?.trip.status).toBe("GENERATING");

    // Advance 5s to trigger poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(result.current.data?.trip.status).toBe("VOTING");
    // Polling stopped — no further calls
    const callCount = mockGetTripView.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mockGetTripView.mock.calls.length).toBe(callCount);
  });
});
