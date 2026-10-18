import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { toast } from "sonner";
import TripDetail from "../TripDetail";
import type { Itinerary, Participant, Trip, TripStatus } from "@/types";

const m = vi.hoisted(() => ({
  get: vi.fn(),
  generate: vi.fn(),
  pickWinner: vi.fn(),
  del: vi.fn(),
  people: vi.fn(),
  its: vi.fn(),
  results: vi.fn(),
  adminVote: vi.fn(),
  resendAll: vi.fn(),
  resendOne: vi.fn(),
  update: vi.fn(),
  newIter: vi.fn(),
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
    trips: {
      get: m.get,
      triggerGeneration: m.generate,
      pickWinner: m.pickWinner,
      delete: m.del,
      triggerNewIteration: m.newIter,
      update: m.update,
    },
    participants: { listByTrip: m.people },
    itineraries: { getByTrip: m.its },
    votes: { getResults: m.results, adminVote: m.adminVote },
    admin: { resendAll: m.resendAll, resendOne: m.resendOne },
  };
});
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => ({ user: { email: "me@x.com" } }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const trip = (status: TripStatus, extra: Partial<Trip> = {}): Trip =>
  ({
    id: 7,
    trip_code: "ABC123",
    title: "Summer trip",
    destination: null,
    proposed_start_date: null,
    proposed_end_date: null,
    num_options: 2,
    status,
    current_iteration: 1,
    max_iterations: 3,
    winner_itinerary_id: null,
    generation_error: null,
    notes: null,
    ...extra,
  }) as Trip;

const itin = (id: number, name: string) =>
  ({
    id,
    iteration_number: 1,
    option_title: name,
    destination_name: name,
    destination_description: "desc",
    daily_itinerary: [],
    total_estimated_budget: 1000,
    currency: "USD",
    highlights: [],
  }) as unknown as Itinerary;

const person = (id: number, email: string, extra: Partial<Participant> = {}) =>
  ({
    id,
    email,
    name: null,
    preferences_submitted: false,
    has_voted_current_iteration: false,
    ...extra,
  }) as Participant;

function Where() {
  const loc = useLocation();
  return <p>at {loc.pathname + loc.search}</p>;
}

function renderAt(url = "/dashboard/trip/7") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route
          path="/dashboard/trip/:tripId"
          element={
            <>
              <TripDetail />
              <Where />
            </>
          }
        />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  m.get.mockResolvedValue(trip("COLLECTING_PREFERENCES"));
  m.people.mockResolvedValue([person(1, "me@x.com"), person(2, "a@x.com")]);
  m.its.mockResolvedValue([]);
  m.results.mockResolvedValue(null);
  m.generate.mockResolvedValue({ message: "ok" });
  m.pickWinner.mockResolvedValue({ message: "ok" });
  m.del.mockResolvedValue(null);
  m.adminVote.mockResolvedValue({});
  m.newIter.mockResolvedValue({ message: "ok" });
  m.update.mockResolvedValue(trip("COLLECTING_PREFERENCES", { title: "Renamed" }));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("TripDetail", () => {
  it("selects the tab from ?tab= and writes switches back to the URL", async () => {
    renderAt("/dashboard/trip/7?tab=participants");
    expect(await screen.findByRole("tab", { name: "Participants (2)" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    await userEvent.click(screen.getByRole("tab", { name: "Overview" }));
    expect(screen.getByText("at /dashboard/trip/7?tab=overview")).toBeInTheDocument();
  });

  it("generates and toasts", async () => {
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: "Generate options" }));
    expect(m.generate).toHaveBeenCalledWith(7);
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
  });

  it("shows the failure and retries", async () => {
    m.get.mockResolvedValue(trip("GENERATION_FAILED", { generation_error: "model fell over" }));
    renderAt();
    expect(await screen.findByText("model fell over")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry generation" }));
    expect(m.generate).toHaveBeenCalledWith(7);
  });

  it("toasts the resend-all summary and errors", async () => {
    m.resendAll.mockResolvedValueOnce({ sent: 2, failed: 1 });
    renderAt("/dashboard/trip/7?tab=participants");
    await userEvent.click(await screen.findByRole("button", { name: "Resend all" }));
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Sent 2, 1 failed");
    });

    m.resendOne.mockRejectedValueOnce(new Error("boom"));
    await userEvent.click(screen.getByRole("button", { name: "Resend email to a@x.com" }));
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Could not send emails.");
    });
  });

  it("picks a winner and finalizes", async () => {
    m.get.mockResolvedValue(trip("VOTING"));
    m.its.mockResolvedValue([itin(10, "Lisbon"), itin(11, "Rome")]);
    renderAt();
    await userEvent.selectOptions(await screen.findByLabelText("Winning option"), "11");
    await userEvent.click(screen.getByRole("button", { name: "Finalize" }));
    expect(m.pickWinner).toHaveBeenCalledWith(7, 11);
  });

  it("deletes after confirming and navigates to the dashboard", async () => {
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: "Delete trip" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Delete trip" }));
    expect(m.del).toHaveBeenCalledWith(7);
    expect(await screen.findByText("at /dashboard")).toBeInTheDocument();
  });

  it("submits the admin ballot in order", async () => {
    m.get.mockResolvedValue(trip("VOTING"));
    m.its.mockResolvedValue([itin(10, "Lisbon"), itin(11, "Rome")]);
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: "Submit vote" }));
    expect(m.adminVote).toHaveBeenCalledWith(7, [10, 11]);
  });

  it("polls while generating without swapping content for skeletons", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    m.get.mockResolvedValue(trip("GENERATING"));
    renderAt();
    expect(await screen.findByText("Building your options")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5100);
    });
    expect(m.get.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Building your options")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading trip" })).not.toBeInTheDocument();
  });

  it("edits the trip in a dialog, then toasts and refetches", async () => {
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: "Edit trip" }));
    const dialog = await screen.findByRole("dialog");
    const title = within(dialog).getByLabelText(/^title/i);
    expect(title).toHaveValue("Summer trip");
    await userEvent.clear(title);
    await userEvent.type(title, "Renamed");
    const callsBefore = m.get.mock.calls.length;
    await userEvent.click(within(dialog).getByRole("button", { name: "Save changes" }));
    await waitFor(() => {
      expect(m.update).toHaveBeenCalledWith(7, expect.objectContaining({ title: "Renamed" }));
      expect(toast.success).toHaveBeenCalledWith("Trip updated.");
    });
    await waitFor(() => {
      expect(m.get.mock.calls.length).toBeGreaterThan(callsBefore);
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("does not offer Edit trip while voting", async () => {
    m.get.mockResolvedValue(trip("VOTING"));
    m.its.mockResolvedValue([itin(10, "Lisbon"), itin(11, "Rome")]);
    renderAt();
    await screen.findByRole("button", { name: "Finalize" });
    expect(screen.queryByRole("button", { name: "Edit trip" })).not.toBeInTheDocument();
  });

  it("starts a new iteration while voting", async () => {
    m.get.mockResolvedValue(trip("VOTING"));
    m.its.mockResolvedValue([itin(10, "Lisbon"), itin(11, "Rome")]);
    renderAt();
    await userEvent.click(await screen.findByRole("button", { name: "Start new iteration" }));
    expect(m.newIter).toHaveBeenCalledWith(7);
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("New round started.");
    });
  });

  it("renders API datetime dates instead of crashing", async () => {
    m.get.mockResolvedValue(
      trip("COLLECTING_PREFERENCES", {
        proposed_start_date: "2025-06-01T00:00:00",
        proposed_end_date: "2025-06-08T00:00:00",
      })
    );
    renderAt();
    expect(await screen.findByText(/2025.*–.*2025/)).toBeInTheDocument();
  });

  it("keeps the page when a poll fails and shows a non-blocking note", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    m.get.mockResolvedValueOnce(trip("GENERATING")).mockRejectedValue(new Error("offline"));
    renderAt();
    await screen.findByText("Building your options");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5100);
    });
    expect(await screen.findByText(/Couldn.t refresh/)).toBeInTheDocument();
    expect(screen.getByText("Building your options")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("clears the picked winner after a new round so a stale option cannot be finalized", async () => {
    m.get.mockResolvedValueOnce(trip("VOTING"));
    m.its.mockResolvedValueOnce([itin(10, "Lisbon"), itin(11, "Rome")]);
    renderAt();
    const select = await screen.findByLabelText("Winning option");
    await userEvent.selectOptions(select, "11");
    expect(screen.getByRole("button", { name: "Finalize" })).toBeEnabled();

    m.get.mockResolvedValue(trip("VOTING", { current_iteration: 2 }));
    m.its.mockResolvedValue([
      itin(10, "Lisbon"),
      itin(11, "Rome"),
      { ...itin(20, "Oslo"), iteration_number: 2 },
    ]);
    await userEvent.click(screen.getByRole("button", { name: "Start new iteration" }));
    await waitFor(() => {
      expect(screen.getByLabelText("Winning option")).toHaveValue("");
    });
    expect(screen.getByRole("button", { name: "Finalize" })).toBeDisabled();
  });

  it("hides the new-iteration control at the iteration cap", async () => {
    m.get.mockResolvedValue(trip("VOTING", { current_iteration: 3 }));
    m.its.mockResolvedValue([{ ...itin(10, "Lisbon"), iteration_number: 3 }]);
    renderAt();
    await screen.findByRole("button", { name: "Finalize" });
    expect(screen.queryByRole("button", { name: "Start new iteration" })).not.toBeInTheDocument();
  });
});
