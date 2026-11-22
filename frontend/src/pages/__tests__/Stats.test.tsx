import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Stats from "../Stats";
import AppShell from "@/components/AppShell";
import { ApiError } from "@/lib/api";
import type { PlatformStats, PromptQuality, TripStatus } from "@/types";

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: false, isLoading: false, user: null, logout: vi.fn() }),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  stats: { get: mockGet },
}));

// jsdom has no matchMedia; the Toaster in AppShell needs it.
beforeAll(() => {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
  })) as unknown as typeof window.matchMedia;
});

const STATUSES: TripStatus[] = [
  "CREATED",
  "COLLECTING_PREFERENCES",
  "GENERATING",
  "GENERATION_FAILED",
  "VOTING",
  "FINALIZED",
];
const days = (f: (i: number) => number) =>
  Array.from({ length: 30 }, (_, i) => ({
    date: `2099-01-${(i + 1).toString().padStart(2, "0")}`,
    trips: f(i),
    tokens_in: f(i) * 10,
    tokens_out: f(i) * 5,
  }));

const empty: PlatformStats = {
  generated_at: "2099-01-30T12:00:00Z",
  totals: {
    trips: 0,
    users: 0,
    participants: 0,
    votes: 0,
    itineraries: 0,
    ai_attempts: 0,
    tokens_in: 0,
    tokens_out: 0,
    cost_usd: 0,
  },
  funnel: STATUSES.map((status) => ({ status, trips: 0 })),
  generation: {
    attempts: 0,
    valid_attempts: 0,
    valid_rate: null,
    runs: 0,
    runs_succeeded: 0,
    attempts_per_run: [],
    finish_reasons: [],
    latency: {
      p50_ms: null,
      p95_ms: null,
      sample_size: 0,
      histogram: Array.from({ length: 7 }, (_, i) => ({
        min_ms: i * 2000,
        max_ms: i === 6 ? null : (i + 1) * 2000,
        attempts: 0,
      })),
    },
    orphaned_attempts: 0,
  },
  by_model: [],
  by_prompt_version: [],
  activity: days(() => 0),
  voting: {
    avg_participants_per_trip: null,
    trips_reached_voting: 0,
    avg_votes_per_trip: null,
    finalized_trips: 0,
    iterations_to_finalize: [],
    cost_per_finalized_trip_usd: null,
  },
  sampling: { row_cap: 5000, truncated: false },
  pricing: { as_of: "2099-01-01", unpriced_models: [] },
  prompt_quality: null,
};

const quality: PromptQuality = {
  run_date: "2099-01-15",
  model: "gen-model",
  judge_model: "judge-model",
  cases: 12,
  versions: ["v3", "v4"].map((prompt_version, i) => ({
    prompt_version,
    cases: 12,
    judged_cases: i === 0 ? 11 : 12,
    all_checks_pass_rate: i === 0 ? 0.5 : 0.75,
    checks: [
      { check: "time_slots", pass_rate: i === 0 ? 0 : 1, cases: 12, gating: false },
      { check: "json_valid", pass_rate: 1, cases: 12, gating: true },
      { check: "destination_respected", pass_rate: i === 0 ? 0.25 : 0.5, cases: 4, gating: true },
    ],
    judge: [
      { criterion: "preference_fit", mean: i === 0 ? 3.5 : 4.25 },
      { criterion: "budget_realism", mean: null },
    ],
    judge_overall: i === 0 ? 3.5 : 4.25,
  })),
};

const populated: PlatformStats = {
  ...empty,
  totals: { ...empty.totals, trips: 12, tokens_in: 1_234_567, cost_usd: 0.000412 },
  funnel: STATUSES.map((status, i) => ({ status, trips: i * 2 })),
  generation: {
    ...empty.generation,
    attempts: 10,
    valid_attempts: 9,
    valid_rate: 0.9,
    runs: 8,
    runs_succeeded: 7,
    attempts_per_run: [
      { attempts: 1, runs: 6 },
      { attempts: 2, runs: 2 },
    ],
    finish_reasons: [
      { finish_reason: "stop", attempts: 9 },
      { finish_reason: null, attempts: 1 },
    ],
    latency: { ...empty.generation.latency, p50_ms: 4200, p95_ms: 9800, sample_size: 10 },
    orphaned_attempts: 2,
  },
  by_model: [
    {
      provider: "google",
      model: "gemini-a",
      attempts: 6,
      valid_attempts: 5,
      tokens_in: 10,
      tokens_out: 5,
      cost_usd: 0.0004123,
    },
    {
      provider: "google",
      model: "gemini-b",
      attempts: 4,
      valid_attempts: 4,
      tokens_in: 20,
      tokens_out: 9,
      cost_usd: null,
    },
  ],
  by_prompt_version: [
    {
      prompt_version: "v4",
      successful_generations: 5,
      itineraries: 15,
      attempts: 7,
      valid_rate: 0.8571,
      latency_p50_ms: 3100,
      latency_p95_ms: 7700,
      tokens_per_itinerary: 1234.4,
      cost_per_itinerary_usd: 0.00321,
    },
    {
      prompt_version: null,
      successful_generations: 2,
      itineraries: 6,
      attempts: 0,
      valid_rate: null,
      latency_p50_ms: null,
      latency_p95_ms: null,
      tokens_per_itinerary: null,
      cost_per_itinerary_usd: null,
    },
  ],
  activity: days((i) => (i === 3 ? 4 : 1)),
  voting: {
    avg_participants_per_trip: 3.5,
    trips_reached_voting: 6,
    avg_votes_per_trip: 2.25,
    finalized_trips: 3,
    iterations_to_finalize: [{ iterations: 1, trips: 3 }],
    cost_per_finalized_trip_usd: 0.0123,
  },
};

function renderStats(ui = <Stats />) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}
const widths = (el: HTMLElement) =>
  [...el.querySelectorAll<HTMLElement>("[style*='width']")].map((b) => b.style.width);

beforeEach(() => {
  vi.clearAllMocks();
  mockGet.mockResolvedValue(populated);
});

describe("Stats", () => {
  it("renders an empty payload with dashes and empty-list lines", async () => {
    mockGet.mockResolvedValue(empty);
    renderStats();
    expect(await screen.findByRole("heading", { name: "Platform stats" })).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(5);
    expect(screen.getByText("No generation runs yet.")).toBeInTheDocument();
    expect(screen.getByText("No AI attempts yet.")).toBeInTheDocument();
    expect(screen.getByText("No successful generations yet.")).toBeInTheDocument();
    expect(screen.getByText("No finalized trips yet.")).toBeInTheDocument();
    expect(screen.getAllByText("Nothing in the last 30 days.")).toHaveLength(2);
    const totals = screen.getByRole("table", { name: "Totals" });
    expect(within(totals).getAllByText("0").length).toBeGreaterThanOrEqual(8);
    const activity = screen.getByRole("table", { name: "Trips created per day" });
    expect(within(activity).getAllByRole("row")).toHaveLength(31);
  });

  it("renders populated lists with labels and differing bar widths", async () => {
    renderStats();
    await screen.findByRole("heading", { name: "Platform stats" });
    const funnel = screen.getByRole("table", { name: /Where trips are now/ });
    for (const label of ["Created", "Collecting", "Generating", "Failed", "Voting", "Finalized"]) {
      expect(within(funnel).getByRole("rowheader", { name: label })).toBeInTheDocument();
    }
    expect(new Set(widths(funnel)).size).toBeGreaterThan(1);
    const caption = within(funnel).getByText("Where trips are now, not history.");
    expect(caption.tagName).toBe("CAPTION");
    expect(funnel).toHaveAccessibleName(/Where trips are now, not history\./);
    expect(screen.getByText("gemini-a")).toBeInTheDocument();
    expect(screen.getByText("gemini-b")).toBeInTheDocument();
    expect(screen.getByText("v4")).toBeInTheDocument();
    expect(screen.getByText("unversioned")).toBeInTheDocument();
    expect(screen.getByText("90.0%")).toBeInTheDocument();
    expect(screen.getByText("7 / 8")).toBeInTheDocument();
    expect(screen.getByText("4.2 s")).toBeInTheDocument();
    expect(screen.getByText("9.8 s")).toBeInTheDocument();
    expect(screen.getByText("none (request failed)")).toBeInTheDocument();
    expect(screen.getByText("1 attempt")).toBeInTheDocument();
    expect(screen.getByText("2 attempts")).toBeInTheDocument();
    expect(screen.getByText("12 s+")).toBeInTheDocument();
    expect(screen.getByText("1,234,567")).toBeInTheDocument();
  });

  it("renders model rows whose provider/model names differ only by a slash split", async () => {
    const row = { attempts: 1, valid_attempts: 1, tokens_in: 1, tokens_out: 1, cost_usd: null };
    mockGet.mockResolvedValue({
      ...populated,
      by_model: [
        { provider: "a", model: "b/c", ...row },
        { provider: "a/b", model: "c", ...row },
      ],
    });
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      renderStats();
      expect(await screen.findByText("b/c")).toBeInTheDocument();
      expect(screen.getByText("c")).toBeInTheDocument();
      // React only warns on duplicate keys; fail if it did.
      expect(errorSpy.mock.calls.filter(([msg]) => String(msg).includes("same key"))).toEqual([]);
    } finally {
      errorSpy.mockRestore();
    }
  });

  it("renders a one-row list", async () => {
    renderStats();
    const rounds = await screen.findByRole("table", { name: /Rounds of options/ });
    expect(within(rounds).getByRole("rowheader", { name: "1 round" })).toBeInTheDocument();
    expect(widths(rounds)).toEqual(["100%"]);
  });

  it("shows the error with Try again that refetches", async () => {
    mockGet.mockRejectedValueOnce(new ApiError(429, "Too many requests"));
    renderStats();
    expect(await screen.findByText("Too many requests")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(mockGet).toHaveBeenCalledTimes(2);
    expect(await screen.findByRole("table", { name: "Totals" })).toBeInTheDocument();
  });

  it("lists the gaps and the truncation note only when truncated", async () => {
    const { unmount } = renderStats();
    await screen.findByRole("heading", { name: "What this measures" });
    for (const t of [
      "A run counts as succeeded when the AI returned a usable response, including the rare run PackVote discarded because the trip was reset while the AI was working.",
      "Runs that failed outright before migration 0002 have no prompt version, so older versions' valid rate and cost leave out their worst runs.",
      "Costs are list-price equivalents as of 2099-01-01. Actual spend on Gemini's free tier is $0.",
      "Attempts refused by PackVote's own AI rate limiter are not logged.",
      "Emails sent are not stored.",
      "There is no finalization timestamp, so time-to-finalize cannot be shown.",
      "Deleted trips drop out of every count except AI attempts, which show as orphaned.",
    ]) {
      expect(screen.getByText(t)).toBeInTheDocument();
    }
    expect(screen.queryByText(/most recent/)).toBeNull();
    unmount();
    mockGet.mockResolvedValue({ ...populated, sampling: { row_cap: 5000, truncated: true } });
    renderStats();
    expect(
      await screen.findByText("Latency and daily activity use the most recent 5,000 rows.")
    ).toBeInTheDocument();
  });

  it("shows list-price costs, with a dash for unpriced models", async () => {
    renderStats();
    await screen.findByRole("heading", { name: "Platform stats" });
    const models = screen.getByRole("region", { name: "AI attempts per provider and model." });
    expect(within(models).getByRole("columnheader", { name: "Cost (list price)" })).toBeVisible();
    expect(within(models).getByText("$0.0004123")).toBeInTheDocument();
    expect(within(models).getByText("—")).toBeInTheDocument();
    const totals = screen.getByRole("table", { name: "Totals" });
    expect(within(totals).getByRole("rowheader", { name: "Cost at list price" })).toBeVisible();
    expect(within(totals).getByText("$0.000412")).toBeInTheDocument();
    expect(screen.getByText("$0.0123")).toBeInTheDocument();
    expect(screen.getByText(/as of 2099-01-01\. Actual spend on Gemini/)).toBeInTheDocument();
  });

  it("renders the per-version columns", async () => {
    renderStats();
    await screen.findByRole("heading", { name: "Platform stats" });
    const t = screen.getByRole("region", { name: /Generations and itineraries count/ });
    for (const h of [
      "Attempts",
      "Valid rate",
      "p50 latency",
      "p95 latency",
      "Tokens / itinerary",
    ]) {
      expect(within(t).getByRole("columnheader", { name: h })).toBeInTheDocument();
    }
    const v4 = within(t).getByText("v4").closest("tr") as HTMLElement;
    for (const text of ["85.7%", "3.1 s", "7.7 s", "1,234", "$0.00321"]) {
      expect(within(v4).getByText(text)).toBeInTheDocument();
    }
    const old = within(t).getByText("unversioned").closest("tr") as HTMLElement;
    expect(within(old).getAllByText("—")).toHaveLength(5);
  });

  it("hides prompt quality when null and shows both versions when present", async () => {
    const { unmount } = renderStats();
    await screen.findByRole("heading", { name: "Platform stats" });
    expect(screen.queryByRole("heading", { name: "Prompt quality" })).toBeNull();
    expect(screen.queryByText(/self-grading/)).toBeNull();
    unmount();
    mockGet.mockResolvedValue({ ...populated, prompt_quality: quality });
    renderStats();
    expect(await screen.findByRole("heading", { name: "Prompt quality" })).toBeInTheDocument();
    const t = screen.getByRole("region", { name: /Offline eval of 12 synthetic cases/ });
    expect(t).toHaveAccessibleName(/2099-01-15.*gen-model.*judge-model/);
    expect(within(t).getByRole("columnheader", { name: "v3" })).toBeInTheDocument();
    expect(within(t).getByRole("columnheader", { name: "v4" })).toBeInTheDocument();
    const rowOf = (name: string) => within(t).getByText(name).closest("tr") as HTMLElement;
    expect(within(rowOf("Pass every check")).getByText("50.0%")).toBeInTheDocument();
    expect(within(rowOf("Pass every check")).getByText("75.0%")).toBeInTheDocument();
    expect(within(rowOf("Destination respected")).getByText("50.0% (4)")).toBeInTheDocument();
    expect(within(rowOf("Preference fit")).getByText("4.25")).toBeInTheDocument();
    expect(within(rowOf("Budget realism")).getAllByText("—")).toHaveLength(2);
    expect(screen.queryByText(/self-grading bias/)).toBeNull();
    expect(screen.getByText(/not live traffic/)).toBeInTheDocument();
    expect(within(rowOf("Judged cases")).getByText("11")).toBeInTheDocument();
  });

  it("marks non-gating checks as not counted and lists them after gating ones", async () => {
    mockGet.mockResolvedValue({ ...populated, prompt_quality: quality });
    renderStats();
    const t = await screen.findByRole("region", { name: /Offline eval of 12 synthetic cases/ });
    const slots = within(t).getByText("Has time-of-day slots").closest("tr") as HTMLElement;
    expect(within(slots).getByText("100.0% (12)")).toBeInTheDocument();
    const gating = within(t).getByText("Destination respected").closest("tr") as HTMLElement;
    const note = within(t).getByText(/Not counted in .Pass every check./);
    const order = (a: HTMLElement, b: HTMLElement) =>
      a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING;
    expect(order(gating, note)).toBeTruthy();
    expect(order(note, slots)).toBeTruthy();
    expect(order(slots, within(t).getByText("Judged cases"))).toBeTruthy();
  });

  it("shows the self-grading caveat only when the judge is the generation model", async () => {
    mockGet.mockResolvedValue({
      ...populated,
      prompt_quality: { ...quality, judge_model: quality.model },
    });
    renderStats();
    expect(await screen.findByText(/self-grading bias/)).toBeInTheDocument();
  });

  it("computes the conversion funnel shares and guards zero", async () => {
    mockGet.mockResolvedValue({
      ...populated,
      totals: { ...populated.totals, trips: 4 },
      voting: {
        ...populated.voting,
        trips_reached_voting: 2,
        finalized_trips: 1,
        iterations_to_finalize: [{ iterations: 1, trips: 1 }],
      },
    });
    const { unmount } = renderStats();
    const funnel = await screen.findByRole("table", { name: /How far trips got/ });
    expect(within(funnel).getByRole("rowheader", { name: "Created" })).toBeInTheDocument();
    expect(
      within(funnel).getByRole("rowheader", { name: "Reached voting (50.0% of created)" })
    ).toBeInTheDocument();
    expect(
      within(funnel).getByRole("rowheader", { name: "Finalized (25.0% of created)" })
    ).toBeInTheDocument();
    const round1 = screen.getByText("Finalized in round 1").nextElementSibling;
    expect(round1).toHaveTextContent("100.0%");
    expect(screen.getByText("Mean rounds to finalize").nextElementSibling).toHaveTextContent("1.0");
    unmount();

    mockGet.mockResolvedValue({
      ...populated,
      voting: {
        ...populated.voting,
        finalized_trips: 4,
        iterations_to_finalize: [
          { iterations: 1, trips: 1 },
          { iterations: 3, trips: 3 },
        ],
      },
    });
    renderStats();
    await screen.findByRole("table", { name: /How far trips got/ });
    expect(screen.getByText("Finalized in round 1").nextElementSibling).toHaveTextContent("25.0%");
    expect(screen.getByText("Mean rounds to finalize").nextElementSibling).toHaveTextContent("2.5");
  });

  it("shows dashes and an empty funnel when there are no trips", async () => {
    mockGet.mockResolvedValue(empty);
    renderStats();
    await screen.findByRole("heading", { name: "Conversion funnel" });
    const funnel = screen.getByRole("table", { name: /How far trips got/ });
    expect(within(funnel).getByText("No trips yet.")).toBeInTheDocument();
    expect(screen.getByText("Finalized in round 1").nextElementSibling).toHaveTextContent("—");
    expect(screen.getByText("Mean rounds to finalize").nextElementSibling).toHaveTextContent("—");
  });

  it("names unpriced models in the caveats", async () => {
    mockGet.mockResolvedValue({
      ...populated,
      pricing: { as_of: "2099-01-01", unpriced_models: ["mystery-1", "mystery-2"] },
    });
    renderStats();
    expect(await screen.findByText(/mystery-1, mystery-2/)).toBeInTheDocument();
  });

  it("has exactly one yellow element and no flip on first render", async () => {
    const { container } = renderStats();
    await screen.findByRole("heading", { name: "What this measures" });
    expect(container.querySelectorAll(".bg-accent")).toHaveLength(1);
    expect(screen.getByRole("link", { name: "Plan a trip" })).toHaveAttribute("href", "/login");
    expect(container.querySelector(".animate-flip")).toBeNull();
  });

  it("is linked from the footer", () => {
    renderStats(<AppShell />);
    expect(screen.getByRole("link", { name: "Platform stats" })).toHaveAttribute("href", "/stats");
  });
});
