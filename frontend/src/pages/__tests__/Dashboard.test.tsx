import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import Dashboard from "../Dashboard";
import type { InvitedTripSummary, TripSummary } from "@/types";

const { mockList, mockInvited } = vi.hoisted(() => ({ mockList: vi.fn(), mockInvited: vi.fn() }));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  trips: { list: mockList, listInvited: mockInvited, create: vi.fn() },
}));

const base: TripSummary = {
  id: 1,
  trip_code: "ABC",
  title: "Lisbon",
  destination: null,
  status: "VOTING",
  participant_count: 4,
  preferences_submitted_count: 3,
  created_at: "2099-01-01T12:00:00",
};
const invitedTrip: InvitedTripSummary = {
  ...base,
  id: 2,
  title: "Rome",
  participant_token: "tok9",
};

function Where() {
  const loc = useLocation();
  return (
    <p>
      at {loc.pathname}
      {loc.search} state={JSON.stringify(loc.state)}
    </p>
  );
}

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route
          path="/dashboard"
          element={
            <>
              <Dashboard />
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
  mockList.mockResolvedValue([base]);
  mockInvited.mockResolvedValue([invitedTrip]);
});

describe("Dashboard", () => {
  it("shows counts and the created row linking to the trip", async () => {
    renderAt("/dashboard");
    expect(await screen.findByRole("tab", { name: "Created (1)" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tab", { name: "Invited (1)" })).toBeInTheDocument();
    const row = screen.getByRole("link", { name: /Lisbon/ });
    expect(row).toHaveAttribute("href", "/dashboard/trip/1");
    expect(row).toHaveTextContent("Surprise me");
    expect(row).toHaveTextContent("3/4");
  });

  it("?tab=invited selects Invited; switching updates the URL; invalid falls back to created", async () => {
    const user = userEvent.setup();
    renderAt("/dashboard?tab=invited");
    const invitedTab = await screen.findByRole("tab", { name: "Invited (1)" });
    expect(invitedTab).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByRole("tab", { name: "Created (1)" }));
    expect(screen.getByText(/at \/dashboard\?tab=created/)).toBeInTheDocument();
  });

  it("falls back to created for an invalid tab", async () => {
    renderAt("/dashboard?tab=nope");
    expect(await screen.findByRole("tab", { name: "Created (1)" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
  });

  it("invited row links to the participant page with dashboard-invited state", async () => {
    const user = userEvent.setup();
    renderAt("/dashboard?tab=invited");
    await user.click(await screen.findByRole("link", { name: /Rome/ }));
    expect(screen.getByText(/at \/trip\/tok9/)).toHaveTextContent('{"from":"dashboard-invited"}');
  });

  it("shows empty states", async () => {
    mockList.mockResolvedValue([]);
    mockInvited.mockResolvedValue([]);
    const user = userEvent.setup();
    renderAt("/dashboard");
    expect(await screen.findByText("No trips yet")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Invited (0)" }));
    expect(screen.getByText("No invitations yet")).toBeInTheDocument();
  });

  it("shows a per-tab error with retry", async () => {
    mockList.mockRejectedValueOnce(new Error("boom"));
    const user = userEvent.setup();
    renderAt("/dashboard");
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("link", { name: /Lisbon/ })).toBeInTheDocument();
  });
});
