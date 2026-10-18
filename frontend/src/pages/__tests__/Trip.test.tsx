import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Trip from "../Trip";
import type { Itinerary, ParticipantTripView, TripStatus } from "@/types";

const { mockView, mockPrefs, mockVote } = vi.hoisted(() => ({
  mockView: vi.fn(),
  mockPrefs: vi.fn(),
  mockVote: vi.fn(),
}));

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(
      public status: number,
      message: string
    ) {
      super(message);
    }
  }
  return {
    ApiError,
    participants: { getTripView: mockView, submitPreferences: mockPrefs },
    votes: { submit: mockVote },
  };
});
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const itin = (id: number, name: string) =>
  ({
    id,
    option_title: name,
    destination_name: name,
    destination_description: "desc",
    daily_itinerary: [],
    total_estimated_budget: 1000,
    currency: "USD",
    highlights: [],
  }) as unknown as Itinerary;

const view = (status: TripStatus, extra: Partial<ParticipantTripView> = {}): ParticipantTripView =>
  ({
    participant: { id: 1, preferences_submitted: false },
    trip: {
      id: 7,
      title: "Summer trip",
      destination: null,
      proposed_start_date: null,
      proposed_end_date: null,
      status,
      winner_itinerary_id: null,
      notes: null,
    },
    participants: [{ id: 1, name: "Ann Lee", preferences_submitted: false }],
    itineraries: [],
    voting_results: null,
    has_voted: false,
    ...extra,
  }) as unknown as ParticipantTripView;

const renderTrip = () =>
  render(
    <MemoryRouter initialEntries={["/trip/tok"]}>
      <Routes>
        <Route path="/trip/:token" element={<Trip />} />
      </Routes>
    </MemoryRouter>
  );

describe("Trip", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows the preference form, then waiting state after submit + refetch", async () => {
    const user = userEvent.setup();
    mockView.mockResolvedValueOnce(view("COLLECTING_PREFERENCES"));
    mockPrefs.mockResolvedValue({});
    renderTrip();
    await screen.findByRole("heading", { name: "Your preferences" });

    mockView.mockResolvedValue(
      view("COLLECTING_PREFERENCES", {
        participant: { id: 1, preferences_submitted: true } as never,
      })
    );
    await user.click(screen.getByRole("button", { name: "Submit preferences" }));
    expect(await screen.findByText("Preferences submitted")).toBeInTheDocument();
    expect(mockPrefs).toHaveBeenCalledWith("tok", expect.objectContaining({ currency: "USD" }));
    expect(mockView).toHaveBeenCalledTimes(2);
  });

  it("shows the participant failure message", async () => {
    mockView.mockResolvedValue(view("GENERATION_FAILED"));
    renderTrip();
    expect(await screen.findByText(/organizer can retry generation/i)).toBeInTheDocument();
  });

  it("submits the ordered ids when voting", async () => {
    const user = userEvent.setup();
    mockView.mockResolvedValue(
      view("VOTING", { itineraries: [itin(1, "Alpha"), itin(2, "Beta")] })
    );
    mockVote.mockResolvedValue({});
    renderTrip();
    await user.click(await screen.findByRole("button", { name: "Move Beta up" }));
    await user.click(screen.getByRole("button", { name: "Submit vote" }));
    expect(mockVote).toHaveBeenCalledWith(7, "tok", [2, 1]);
  });

  it("labels re-votes as updates", async () => {
    mockView.mockResolvedValue(
      view("VOTING", { itineraries: [itin(1, "Alpha")], has_voted: true })
    );
    renderTrip();
    expect(await screen.findByRole("button", { name: "Update vote" })).toBeInTheDocument();
  });

  it("treats a cleared (empty) destination as unset", async () => {
    const v = view("COLLECTING_PREFERENCES");
    v.trip.destination = "";
    mockView.mockResolvedValue(v);
    renderTrip();
    expect(await screen.findByText("Destination TBD")).toBeInTheDocument();
    expect(screen.queryByText("Organizer's proposal")).not.toBeInTheDocument();
  });

  it("shows the winner when finalized", async () => {
    const v = view("FINALIZED", { itineraries: [itin(1, "Alpha")] });
    v.trip.winner_itinerary_id = 1;
    mockView.mockResolvedValue(v);
    renderTrip();
    expect(await screen.findByText("Your group has a winner")).toBeInTheDocument();
  });

  it("falls back to the winner's destination in the header when the trip has none", async () => {
    const v = view("FINALIZED", {
      itineraries: [{ ...itin(1, "Island week"), destination_name: "Naxos, Greece" }],
    });
    v.trip.winner_itinerary_id = 1;
    mockView.mockResolvedValue(v);
    renderTrip();
    await screen.findByText("Your group has a winner");
    expect(screen.queryByText("Destination TBD")).not.toBeInTheDocument();
    // Once in the header, once in the winner card.
    expect(screen.getAllByText("Naxos, Greece")).toHaveLength(2);
  });

  it("polls while generating without dropping content", async () => {
    vi.useFakeTimers();
    mockView
      .mockResolvedValueOnce(view("GENERATING"))
      .mockResolvedValue(view("VOTING", { itineraries: [itin(1, "Alpha")] }));
    renderTrip();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("Building your options")).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(screen.getByText("Summer trip")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit vote" })).toBeInTheDocument();
    expect(mockView).toHaveBeenCalledTimes(2);
  });

  it("shows an error with a link to /join", async () => {
    mockView.mockRejectedValue(new Error("Nope"));
    renderTrip();
    expect(await screen.findByRole("alert")).toHaveTextContent("Nope");
    expect(screen.getByRole("link", { name: "Back to join page" })).toHaveAttribute(
      "href",
      "/join"
    );
  });
});
