import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import { ResultsBoard, boardRows } from "../ResultsBoard";
import type { Itinerary, VoteRoundResult, VotingResults } from "@/types";

const opt = (id: number, name: string) =>
  ({ id, destination_name: name, option_title: null }) as Itinerary;
const options = [opt(1, "Lisbon"), opt(2, "Porto"), opt(3, "Faro")];

const round = (
  n: number,
  results: Record<number, number>,
  eliminated: number | null,
  winner: number | null
): VoteRoundResult => ({
  round_number: n,
  results,
  eliminated_option_id: eliminated,
  winner_id: winner,
});

const make = (
  rounds: VoteRoundResult[],
  winner_id: number | null = null,
  iteration_number = 1
): VotingResults => ({
  trip_id: 1,
  iteration_number,
  rounds,
  winner_id,
  is_complete: true,
});

// Porto is eliminated in round 1; Lisbon wins round 2 against Faro.
const elimination = make(
  [round(1, { 1: 3, 2: 1, 3: 2 }, 2, null), round(2, { 1: 3, 3: 3 }, null, 1)],
  1
);

describe("boardRows", () => {
  it("2-round elimination: winner BOARDING, eliminated row ELIMINATED, rest RUNNER-UP", () => {
    const rows = boardRows(elimination, options);
    expect(rows.map((r) => [r.id, r.status])).toEqual([
      [1, "BOARDING"],
      [3, "RUNNER-UP"],
      [2, "ELIMINATED"],
    ]);
    const porto = rows.find((r) => r.id === 2);
    expect(porto?.counts).toEqual([1, null]);
    expect(porto?.outRound).toBe(1);
    expect(rows[0].counts).toEqual([3, 3]);
    expect(rows[0].outRound).toBeNull();
  });

  it("two options: winner BOARDING and the other ELIMINATED", () => {
    const rows = boardRows(
      make([round(1, { 1: 2, 2: 1 }, 2, null), round(2, { 1: 2 }, null, 1)], 1),
      options
    );
    expect(rows.map((r) => [r.id, r.status, r.counts])).toEqual([
      [1, "BOARDING", [2, 2]],
      [2, "ELIMINATED", [1, null]],
    ]);
  });

  it("3-way round-1 tie marks every row TIED", () => {
    const rows = boardRows(make([round(1, { 1: 1, 2: 1, 3: 1 }, null, null)]), options);
    expect(rows).toHaveLength(3);
    expect(rows.every((r) => r.status === "TIED" && r.outRound === null)).toBe(true);
  });

  it("eliminated-then-tie: one ELIMINATED, two TIED", () => {
    const rows = boardRows(
      make([round(1, { 1: 2, 2: 2, 3: 1 }, 3, null), round(2, { 1: 2, 2: 2 }, null, null)]),
      options
    );
    expect(rows.map((r) => [r.id, r.status])).toEqual([
      [1, "TIED"],
      [2, "TIED"],
      [3, "ELIMINATED"],
    ]);
  });

  it("returns [] when there are no rounds", () => {
    expect(boardRows(make([]), options)).toEqual([]);
  });

  it("sorts by round-1 count desc, then id asc", () => {
    const rows = boardRows(make([round(1, { 3: 2, 1: 1, 2: 2 }, null, null)]), options);
    expect(rows.map((r) => r.id)).toEqual([2, 3, 1]);
  });

  it("falls back to #id when the option is unknown", () => {
    const [row] = boardRows(make([round(1, { 9: 1 }, null, 9)]), options);
    expect(row.title).toBe("#9");
  });
});

describe("ResultsBoard", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const rowOf = (title: string) => screen.getByText(title).closest("tr");

  it("shows an empty message with zero rounds", () => {
    render(<ResultsBoard results={make([])} options={options} final />);
    expect(screen.getByText("No votes yet")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows the organizer override only when it differs from the vote winner", () => {
    const { rerender } = render(
      <ResultsBoard results={{ ...elimination, winner_id: 3 }} options={options} final />
    );
    expect(screen.getByText("Organizer finalized Faro")).toBeInTheDocument();
    rerender(<ResultsBoard results={elimination} options={options} final />);
    expect(screen.queryByText(/Organizer finalized/)).not.toBeInTheDocument();
  });

  it("final=false: leader reads Leading and no row is highlighted", () => {
    render(<ResultsBoard results={elimination} options={options} final={false} />);
    expect(screen.getByText("Leading")).toBeInTheDocument();
    expect(screen.queryByText("Boarding")).not.toBeInTheDocument();
    for (const row of screen.getAllByRole("row")) expect(row).not.toHaveClass("bg-accent");
  });

  it("final=true: winner reads Boarding on the accent row", () => {
    render(<ResultsBoard results={elimination} options={options} final />);
    expect(screen.getByText("Boarding")).toBeInTheDocument();
    expect(screen.queryByText("Leading")).not.toBeInTheDocument();
    expect(rowOf("Lisbon")).toHaveClass("bg-accent");
    expect(rowOf("Porto")).not.toHaveClass("bg-accent");
    expect(screen.getByText("Eliminated")).toBeInTheDocument();
    expect(screen.getByText("Runner-up")).toBeInTheDocument();
  });

  it("shows a title longer than its flap text visibly, one node, at every width", () => {
    const long = [opt(1, "Old Town Cultural Escape"), opt(2, "Porto")];
    render(
      <ResultsBoard results={make([round(1, { 1: 2, 2: 1 }, null, 1)], 1)} options={long} final />
    );
    expect(screen.getByText("Old Town Cultural Escape")).not.toHaveClass(
      "sr-only",
      "max-md:sr-only"
    );
    // Equal to its flap text: screen-reader only.
    expect(screen.getByText("Porto")).toHaveClass("sr-only");
  });

  it("override: the organizer's pick gets the yellow Boarding row, the vote winner reads Won vote", () => {
    // Vote winner is Lisbon (1); the organizer picked the eliminated Porto (2).
    render(<ResultsBoard results={{ ...elimination, winner_id: 2 }} options={options} final />);
    expect(screen.getByText("Organizer finalized Porto")).toBeInTheDocument();
    expect(rowOf("Porto")).toHaveClass("bg-accent");
    expect(within(rowOf("Porto") as HTMLElement).getByText("Boarding")).toBeInTheDocument();
    expect(rowOf("Lisbon")).not.toHaveClass("bg-accent");
    expect(within(rowOf("Lisbon") as HTMLElement).getByText("Won vote")).toBeInTheDocument();
    expect(
      screen.getAllByRole("row").filter((r) => r.classList.contains("bg-accent"))
    ).toHaveLength(1);
  });

  it("final=true with a tie: Tied rows, no highlight", () => {
    render(
      <ResultsBoard
        results={make([round(1, { 1: 1, 2: 1, 3: 1 }, null, null)])}
        options={options}
        final
      />
    );
    expect(screen.getAllByText("Tied")).toHaveLength(3);
    for (const row of screen.getAllByRole("row")) expect(row).not.toHaveClass("bg-accent");
  });

  it("captions ballots and iteration", () => {
    render(<ResultsBoard results={make(elimination.rounds, 1, 2)} options={options} final />);
    expect(screen.getByText("6 ballots · Iteration 2")).toBeInTheDocument();
  });

  it("singular ballot", () => {
    render(
      <ResultsBoard results={make([round(1, { 1: 1 }, null, 1)], 1)} options={options} final />
    );
    expect(screen.getByText("1 ballot · Iteration 1")).toBeInTheDocument();
  });

  it("offers Replay normally", () => {
    render(<ResultsBoard results={elimination} options={options} final />);
    expect(screen.getByRole("button", { name: "Replay" })).toBeInTheDocument();
  });

  it("hides Replay under prefers-reduced-motion", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn((q: string) => ({ matches: q === "(prefers-reduced-motion: reduce)" }))
    );
    render(<ResultsBoard results={elimination} options={options} final />);
    expect(screen.queryByRole("button", { name: "Replay" })).not.toBeInTheDocument();
    expect(screen.getByText("Boarding")).toBeInTheDocument();
  });

  it("is already settled when mounted without playOnMount", () => {
    const { container } = render(<ResultsBoard results={elimination} options={options} final />);
    expect(container.querySelector(".opacity-0")).toBeNull();
    expect(container.querySelector(".animate-flip")).toBeNull();
  });

  it("replays when the rounds change, then settles", () => {
    vi.useFakeTimers();
    const { container, rerender } = render(
      <ResultsBoard results={elimination} options={options} final />
    );
    const changed = make([round(1, { 1: 4, 2: 1, 3: 2 }, 2, null), elimination.rounds[1]], 1);
    rerender(<ResultsBoard results={changed} options={options} final />);
    expect(container.querySelector(".opacity-0")).not.toBeNull();
    act(() => {
      vi.advanceTimersByTime(650 * changed.rounds.length * 2 + 50);
    });
    expect(container.querySelector(".opacity-0")).toBeNull();
    expect(container.querySelector(".animate-flip")).not.toBeNull();
  });

  it("does not replay when polled data is identical", () => {
    vi.useFakeTimers();
    const { container, rerender } = render(
      <ResultsBoard results={elimination} options={options} final />
    );
    rerender(
      <ResultsBoard
        results={JSON.parse(JSON.stringify(elimination)) as VotingResults}
        options={options}
        final
      />
    );
    expect(container.querySelector(".opacity-0")).toBeNull();
    expect(container.querySelector(".animate-flip")).toBeNull();
  });

  it("plays on mount when asked", () => {
    vi.useFakeTimers();
    const { container } = render(
      <ResultsBoard results={elimination} options={options} final playOnMount />
    );
    expect(container.querySelector(".opacity-0")).not.toBeNull();
    act(() => {
      vi.advanceTimersByTime(650 * 4 + 50);
    });
    expect(container.querySelector(".opacity-0")).toBeNull();
  });
});
