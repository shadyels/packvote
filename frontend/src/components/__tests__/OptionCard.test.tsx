import { describe, it, expect } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OptionCard } from "../OptionCard";
import type { Itinerary } from "@/types";

const day = (n: number, cost: number | null) => ({
  day_number: n,
  title: `Title ${n.toString()}`,
  estimated_cost: null,
  activities: [
    { time: "09:00", title: `Act ${n.toString()}`, description: "d", estimated_cost: cost },
  ],
});

const option = {
  id: 1,
  destination_name: "Lisbon",
  option_title: null,
  destination_description: "desc",
  total_estimated_budget: 1000,
  currency: "USD",
  highlights: [],
  match_reasoning: "",
  daily_itinerary: [day(1, 25), day(2, null), day(3, null)],
} as unknown as Itinerary;

async function open() {
  render(<OptionCard option={option} />);
  await userEvent.click(screen.getByRole("button", { name: "Day-by-day" }));
  return screen.findByRole("dialog");
}

describe("OptionCard day-by-day", () => {
  it("opens on day 1 and steps with Next/Previous", async () => {
    const dialog = await open();
    expect(within(dialog).getByText("1 of 3")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /Previous/ })).toBeDisabled();
    await userEvent.click(within(dialog).getByRole("button", { name: /Next/ }));
    expect(within(dialog).getByText("2 of 3")).toBeInTheDocument();
    expect(within(dialog).getByText("Act 2")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: /Previous/ }));
    expect(within(dialog).getByText("1 of 3")).toBeInTheDocument();
  });

  it("moves with ArrowRight/ArrowLeft and clamps at the ends", async () => {
    const dialog = await open();
    await userEvent.keyboard("{ArrowLeft}");
    expect(within(dialog).getByText("1 of 3")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(within(dialog).getByText("3 of 3")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /Next/ })).toBeDisabled();
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(within(dialog).getByText("2 of 3")).toBeInTheDocument();
  });

  it("shows per-person cost only when estimated_cost is not null", async () => {
    const dialog = await open();
    expect(within(dialog).getByText(/per person/)).toHaveTextContent("~USD25 per person");
    await userEvent.click(within(dialog).getByRole("button", { name: /Next/ }));
    expect(within(dialog).queryByText(/per person/)).not.toBeInTheDocument();
  });
});
