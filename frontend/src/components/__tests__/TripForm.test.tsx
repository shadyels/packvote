import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TripForm } from "../TripForm";
import { maxTripDays } from "@/lib/trip";
import type { Trip } from "@/types";

const { mockCreate, mockUpdate } = vi.hoisted(() => ({ mockCreate: vi.fn(), mockUpdate: vi.fn() }));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  trips: { create: mockCreate, update: mockUpdate },
}));

const trip: Trip = {
  id: 7,
  trip_code: "ABC123",
  creator_id: 1,
  title: "Lisbon",
  destination: "Portugal",
  proposed_start_date: "2099-06-01T00:00:00",
  proposed_end_date: "2099-06-04T00:00:00",
  num_options: 3,
  status: "CREATED",
  current_iteration: 1,
  max_iterations: 3,
  winner_itinerary_id: null,
  generation_error: null,
  notes: "bring sunscreen",
  created_at: "2099-01-01T00:00:00",
};

const setDate = (label: string, value: string) => {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TripForm create", () => {
  it("rejects a date range one day over the cap and accepts the boundary", async () => {
    const cap = maxTripDays(3);
    mockCreate.mockResolvedValue(trip);
    const user = userEvent.setup();
    render(<TripForm onDone={vi.fn()} />);
    await user.type(screen.getByLabelText(/^title/i), "T");
    await user.type(screen.getByLabelText("Participant email 1"), "a@b.co");
    setDate("Earliest start", "2099-01-01");
    // day N after 2099-01-01: Jan has 31 days, so stay inside January for small caps
    const day = (n: number) => `2099-01-${(1 + n).toString().padStart(2, "0")}`;

    setDate("Latest end", day(cap + 1));
    await user.click(screen.getByRole("button", { name: "Create trip" }));
    expect(
      await screen.findByText(
        `Date range too long — max ${cap.toString()} days for 3 itinerary options.`
      )
    ).toBeInTheDocument();
    expect(mockCreate).not.toHaveBeenCalled();

    setDate("Latest end", day(cap));
    await user.click(screen.getByRole("button", { name: "Create trip" }));
    expect(mockCreate).toHaveBeenCalledTimes(1);
  });

  it("adds and removes participant rows and requires at least one email", async () => {
    const user = userEvent.setup();
    render(<TripForm onDone={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /remove participant/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /add participant/i }));
    expect(screen.getAllByLabelText(/participant email/i)).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Remove participant 2" }));
    expect(screen.getAllByLabelText(/participant email/i)).toHaveLength(1);

    await user.type(screen.getByLabelText(/^title/i), "T");
    await user.click(screen.getByRole("button", { name: "Create trip" }));
    expect(await screen.findByText("Add at least one participant email.")).toBeInTheDocument();
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("sends the payload and reports the created trip", async () => {
    mockCreate.mockResolvedValue(trip);
    const onDone = vi.fn();
    const user = userEvent.setup();
    render(<TripForm onDone={onDone} />);
    await user.type(screen.getByLabelText(/^title/i), " Trip ");
    await user.type(screen.getByLabelText("Participant email 1"), "a@b.co");
    await user.click(screen.getByRole("button", { name: "Create trip" }));
    await screen.findByRole("button", { name: "Create trip" });
    expect(mockCreate).toHaveBeenCalledWith({
      title: "Trip",
      num_options: 3,
      proposed_start_date: undefined,
      proposed_end_date: undefined,
      destination: undefined,
      notes: undefined,
      participant_emails: ["a@b.co"],
    });
    expect(onDone).toHaveBeenCalledWith(trip);
  });
});

describe("TripForm edit", () => {
  it("prefills from the trip, has no email list, and sends '' for cleared destination/notes", async () => {
    mockUpdate.mockResolvedValue(trip);
    const user = userEvent.setup();
    render(<TripForm trip={trip} onDone={vi.fn()} />);
    expect(screen.getByLabelText(/^title/i)).toHaveValue("Lisbon");
    expect(screen.getByLabelText("Earliest start")).toHaveValue("2099-06-01");
    expect(screen.queryByLabelText(/participant email/i)).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText("Destination"));
    await user.clear(screen.getByLabelText("Notes"));
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await screen.findByRole("button", { name: "Save changes" });
    expect(mockUpdate).toHaveBeenCalledWith(7, {
      title: "Lisbon",
      num_options: 3,
      proposed_start_date: "2099-06-01",
      proposed_end_date: "2099-06-04",
      destination: "",
      notes: "",
    });
  });
});
