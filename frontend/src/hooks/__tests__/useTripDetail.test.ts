import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useTripDetail } from "../useTripDetail";
import type { Itinerary, Participant, Trip, VotingResults } from "@/types";

vi.mock("@/lib/api", () => ({
  trips: { get: vi.fn() },
  participants: { listByTrip: vi.fn() },
  itineraries: { getByTrip: vi.fn() },
  votes: { getResults: vi.fn() },
}));

import * as apiModule from "@/lib/api";
const mockTripsGet = vi.mocked(apiModule.trips.get);
const mockParticipantsList = vi.mocked(apiModule.participants.listByTrip);
const mockItinerariesGet = vi.mocked(apiModule.itineraries.getByTrip);
const mockVotesGetResults = vi.mocked(apiModule.votes.getResults);

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeTrip(status: Trip["status"] = "COLLECTING_PREFERENCES"): Trip {
  return {
    id: 1,
    trip_code: "ABCD1234",
    creator_id: 99,
    title: "Test Trip",
    destination: null,
    proposed_start_date: null,
    proposed_end_date: null,
    num_options: 3,
    status,
    current_iteration: 1,
    max_iterations: 10,
    winner_itinerary_id: null,
    generation_error: null,
    notes: null,
    created_at: "2024-01-01",
  };
}

const FAKE_PARTICIPANTS: Participant[] = [
  {
    id: 1,
    trip_id: 1,
    email: "alice@test.com",
    name: "Alice",
    preferences_submitted: true,
    has_voted_current_iteration: false,
    created_at: "2024-01-01",
  },
];

const FAKE_ITINERARIES: Itinerary[] = [
  {
    id: 10,
    trip_id: 1,
    iteration_number: 1,
    destination_name: "Paris",
    destination_description: "City of light",
    daily_itinerary_json: "[]",
    total_estimated_budget: 1500,
    currency: "EUR",
    match_reasoning: "great",
    highlights: "[]",
    model_used: null,
    provider: null,
    created_at: "2024-01-01",
    estimated_cost: null,
    price_last_updated: null,
    price_source: null,
  },
];

const FAKE_VOTING_RESULTS: VotingResults = {
  trip_id: 1,
  iteration_number: 1,
  is_complete: true,
  winner_id: 10,
  rounds: [],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useTripDetail", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fetches trip, participants, and itineraries on mount", async () => {
    const trip = makeTrip("COLLECTING_PREFERENCES");
    mockTripsGet.mockResolvedValue(trip);
    mockParticipantsList.mockResolvedValue(FAKE_PARTICIPANTS);
    mockItinerariesGet.mockResolvedValue(FAKE_ITINERARIES);

    const { result } = renderHook(() => useTripDetail(1));
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.trip).toEqual(trip);
    expect(result.current.participants).toEqual(FAKE_PARTICIPANTS);
    expect(result.current.itineraries).toEqual(FAKE_ITINERARIES);
    expect(result.current.votingResults).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("fetches voting results when trip is in VOTING status", async () => {
    mockTripsGet.mockResolvedValue(makeTrip("VOTING"));
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);
    mockVotesGetResults.mockResolvedValue(FAKE_VOTING_RESULTS);

    const { result } = renderHook(() => useTripDetail(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockVotesGetResults).toHaveBeenCalledWith(1);
    expect(result.current.votingResults).toEqual(FAKE_VOTING_RESULTS);
  });

  it("fetches voting results when trip is in FINALIZED status", async () => {
    mockTripsGet.mockResolvedValue(makeTrip("FINALIZED"));
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);
    mockVotesGetResults.mockResolvedValue(FAKE_VOTING_RESULTS);

    const { result } = renderHook(() => useTripDetail(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockVotesGetResults).toHaveBeenCalledWith(1);
  });

  it("skips voting results when trip is COLLECTING_PREFERENCES", async () => {
    mockTripsGet.mockResolvedValue(makeTrip("COLLECTING_PREFERENCES"));
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);

    const { result } = renderHook(() => useTripDetail(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockVotesGetResults).not.toHaveBeenCalled();
    expect(result.current.votingResults).toBeNull();
  });

  it("gracefully degrades when participants and itineraries fail — returns empty arrays, no error", async () => {
    // fetchAll uses Promise.allSettled so sub-fetch failures are silent:
    // participants and itineraries fall back to [], trip is still populated.
    mockTripsGet.mockResolvedValue(makeTrip("COLLECTING_PREFERENCES"));
    mockParticipantsList.mockRejectedValue(new Error("403 Forbidden"));
    mockItinerariesGet.mockRejectedValue(new Error("500 Server Error"));

    const { result } = renderHook(() => useTripDetail(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.trip).not.toBeNull();
    expect(result.current.participants).toEqual([]);
    expect(result.current.itineraries).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("gracefully degrades when voting results fail — votingResults stays null, no error", async () => {
    mockTripsGet.mockResolvedValue(makeTrip("VOTING"));
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);
    mockVotesGetResults.mockRejectedValue(new Error("not available yet"));

    const { result } = renderHook(() => useTripDetail(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.votingResults).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("refetch() triggers a new full fetch", async () => {
    mockTripsGet.mockResolvedValue(makeTrip());
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);

    const { result } = renderHook(() => useTripDetail(1));
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockTripsGet).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refetch();
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockTripsGet).toHaveBeenCalledTimes(2);
  });

  it("polls trips.get every 5s while status is GENERATING", async () => {
    vi.useFakeTimers();
    const generatingTrip = makeTrip("GENERATING");

    // Both the initial fetchAll and each poll call need mock values for trips.get
    mockTripsGet.mockResolvedValue(generatingTrip);
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);

    renderHook(() => useTripDetail(1));

    // Flush initial load (advanceByTime(0) drains microtask queue without firing intervals)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    const callsAfterLoad = mockTripsGet.mock.calls.length; // 1 from fetchAll

    // Advance 5s — one poll tick fires
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mockTripsGet.mock.calls.length).toBe(callsAfterLoad + 1);

    // Advance another 5s — second poll tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mockTripsGet.mock.calls.length).toBe(callsAfterLoad + 2);
  });

  it("stops polling when status changes from GENERATING to another status", async () => {
    vi.useFakeTimers();
    const generatingTrip = makeTrip("GENERATING");
    const votingTrip = makeTrip("VOTING");

    mockTripsGet.mockResolvedValue(generatingTrip);
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);

    renderHook(() => useTripDetail(1));

    // Flush initial load
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // First poll tick returns VOTING → stops polling
    mockTripsGet.mockResolvedValue(votingTrip);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    // Allow microtasks from the stopPolling + setTick refetch cycle to settle
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    // Record call count after polling stopped
    const callCount = mockTripsGet.mock.calls.length;

    // Advance another 10s — interval should NOT fire again
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(mockTripsGet.mock.calls.length).toBe(callCount);
  });

  it("does not start polling when status is not GENERATING", async () => {
    vi.useFakeTimers();
    mockTripsGet.mockResolvedValue(makeTrip("VOTING"));
    mockParticipantsList.mockResolvedValue([]);
    mockItinerariesGet.mockResolvedValue([]);
    mockVotesGetResults.mockResolvedValue(FAKE_VOTING_RESULTS);

    renderHook(() => useTripDetail(1));

    // Use runAllTimersAsync — safe here because VOTING never sets up an interval
    await act(async () => {
      await vi.runAllTimersAsync();
    });

    const callCount = mockTripsGet.mock.calls.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });
    expect(mockTripsGet.mock.calls.length).toBe(callCount);
  });
});
