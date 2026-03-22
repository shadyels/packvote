import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import TripPage from "../TripPage";
import type { ParticipantTripView } from "@/types";

// ---------------------------------------------------------------------------
// Mock child components so TripPage tests focus on routing logic only
// ---------------------------------------------------------------------------

vi.mock("@/components/trip/TripHeader", () => ({
  TripHeader: () => <div data-testid="trip-header" />,
}));
vi.mock("@/components/trip/ParticipantProgress", () => ({
  ParticipantProgress: () => <div data-testid="participant-progress" />,
}));
vi.mock("@/components/trip/PreferenceForm", () => ({
  PreferenceForm: () => <div data-testid="preference-form" />,
}));
vi.mock("@/components/trip/WaitingScreen", () => ({
  WaitingScreen: () => <div data-testid="waiting-screen" />,
}));
vi.mock("@/components/trip/GeneratingScreen", () => ({
  GeneratingScreen: () => <div data-testid="generating-screen" />,
}));
vi.mock("@/components/trip/VotingForm", () => ({
  VotingForm: () => <div data-testid="voting-form" />,
}));
vi.mock("@/components/trip/WinnerDisplay", () => ({
  WinnerDisplay: () => <div data-testid="winner-display" />,
}));

// ---------------------------------------------------------------------------
// Mock useTripView
// ---------------------------------------------------------------------------

const mockUseTripView = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/useTripView", () => ({
  useTripView: mockUseTripView,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeTripView(
  status: ParticipantTripView["trip"]["status"],
  overrides: Partial<ParticipantTripView> = {}
): ParticipantTripView {
  return {
    participant: {
      id: 1,
      trip_id: 1,
      email: "p@test.com",
      name: null,
      preferences_submitted: false,
      created_at: "2024-01-01",
    },
    trip: {
      id: 1,
      title: "Test Trip",
      destination: "Paris",
      proposed_start_date: null,
      proposed_end_date: null,
      status,
      num_options: 3,
      current_iteration: 1,
      winner_itinerary_id: null,
      generation_error: null,
    },
    participants: [],
    itineraries: [],
    voting_results: null,
    has_voted: false,
    ...overrides,
  };
}

function renderAtToken(token = "test-token") {
  return render(
    <MemoryRouter initialEntries={[`/trip/${token}`]}>
      <Routes>
        <Route path="/trip/:token" element={<TripPage />} />
      </Routes>
    </MemoryRouter>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("TripPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows skeleton/loading while data is loading", () => {
    mockUseTripView.mockReturnValue({
      isLoading: true,
      data: null,
      error: null,
      refetch: vi.fn(),
    });
    renderAtToken();
    // Loading state renders pulse divs (no specific test-ids, check absence of content)
    expect(screen.queryByTestId("trip-header")).not.toBeInTheDocument();
    expect(screen.queryByTestId("preference-form")).not.toBeInTheDocument();
  });

  it("shows error message and back link on error", () => {
    mockUseTripView.mockReturnValue({
      isLoading: false,
      data: null,
      error: "Trip not found",
      refetch: vi.fn(),
    });
    renderAtToken();
    expect(screen.getByText(/trip not found/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /back to join page/i })
    ).toBeInTheDocument();
  });

  it("shows PreferenceForm when COLLECTING_PREFERENCES and not yet submitted", () => {
    mockUseTripView.mockReturnValue({
      isLoading: false,
      data: makeTripView("COLLECTING_PREFERENCES", {
        participant: {
          id: 1,
          trip_id: 1,
          email: "p@test.com",
          name: null,
          preferences_submitted: false,
          created_at: "2024-01-01",
        },
      }),
      error: null,
      refetch: vi.fn(),
    });
    renderAtToken();
    expect(screen.getByTestId("preference-form")).toBeInTheDocument();
    expect(screen.queryByTestId("waiting-screen")).not.toBeInTheDocument();
  });

  it("shows WaitingScreen when COLLECTING_PREFERENCES and already submitted", () => {
    mockUseTripView.mockReturnValue({
      isLoading: false,
      data: makeTripView("COLLECTING_PREFERENCES", {
        participant: {
          id: 1,
          trip_id: 1,
          email: "p@test.com",
          name: null,
          preferences_submitted: true,
          created_at: "2024-01-01",
        },
      }),
      error: null,
      refetch: vi.fn(),
    });
    renderAtToken();
    expect(screen.getByTestId("waiting-screen")).toBeInTheDocument();
    expect(screen.queryByTestId("preference-form")).not.toBeInTheDocument();
  });

  it("shows GeneratingScreen when status is GENERATING", () => {
    mockUseTripView.mockReturnValue({
      isLoading: false,
      data: makeTripView("GENERATING"),
      error: null,
      refetch: vi.fn(),
    });
    renderAtToken();
    expect(screen.getByTestId("generating-screen")).toBeInTheDocument();
  });

  it("shows VotingForm when status is VOTING", () => {
    mockUseTripView.mockReturnValue({
      isLoading: false,
      data: makeTripView("VOTING"),
      error: null,
      refetch: vi.fn(),
    });
    renderAtToken();
    expect(screen.getByTestId("voting-form")).toBeInTheDocument();
  });

  it("shows WinnerDisplay when FINALIZED with a winner", () => {
    const itinerary = {
      id: 99,
      trip_id: 1,
      iteration_number: 1,
      destination_name: "Paris",
      destination_description: "City of Light",
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
    };
    mockUseTripView.mockReturnValue({
      isLoading: false,
      data: makeTripView("FINALIZED", {
        trip: {
          id: 1,
          title: "Test Trip",
          destination: "Paris",
          proposed_start_date: null,
          proposed_end_date: null,
          status: "FINALIZED",
          num_options: 3,
          current_iteration: 1,
          winner_itinerary_id: 99,
          generation_error: null,
        },
        itineraries: [itinerary],
      }),
      error: null,
      refetch: vi.fn(),
    });
    renderAtToken();
    expect(screen.getByTestId("winner-display")).toBeInTheDocument();
  });
});
