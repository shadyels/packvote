import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { Results } from "../Results";
import type { Itinerary, VotingResults } from "@/types";

const opt = (id: number, name: string) => ({ id, destination_name: name }) as unknown as Itinerary;
const options = [opt(1, "Lisbon"), opt(2, "Rome"), opt(3, "Oslo")];

const base: VotingResults = {
  trip_id: 7,
  iteration_number: 1,
  rounds: [],
  winner_id: null,
  is_complete: false,
};

describe("Results", () => {
  it("shows an empty state when there are no rounds", () => {
    render(<Results results={base} options={options} />);
    expect(screen.getByText("No votes recorded yet.")).toBeInTheDocument();
  });

  it("shows the winner, per-round votes and the eliminated badge", () => {
    render(
      <Results
        options={options}
        results={{
          ...base,
          winner_id: 1,
          is_complete: true,
          rounds: [
            {
              round_number: 1,
              results: { 1: 3, 2: 2, 3: 1 },
              eliminated_option_id: 3,
              winner_id: null,
            },
            { round_number: 2, results: { 1: 4, 2: 2 }, eliminated_option_id: null, winner_id: 1 },
          ],
        }}
      />
    );
    expect(screen.getByText("Winner: Lisbon")).toBeInTheDocument();
    const r1 = screen.getByRole("region", { name: "Round 1" });
    const oslo = within(r1).getByText("Oslo").closest("li") as HTMLElement;
    expect(within(oslo).getByText("Eliminated")).toBeInTheDocument();
    expect(within(oslo).getByText("1")).toBeInTheDocument();
    expect(within(r1).queryByText("Winner")).not.toBeInTheDocument();
    const r2 = screen.getByRole("region", { name: "Round 2" });
    const lisbon = within(r2).getByText("Lisbon").closest("li") as HTMLElement;
    expect(within(lisbon).getByText("Winner")).toBeInTheDocument();
    expect(within(lisbon).getByText("4")).toBeInTheDocument();
    expect(within(r2).queryByText("Eliminated")).not.toBeInTheDocument();
  });
});
