import { describe, it, expect } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OptionCard } from "../OptionCard";
import type { Itinerary } from "@/types";

const act = (title: string, time: string | null) => ({
  time,
  title,
  description: "d",
  estimated_cost: null,
});

const day = (n: number) => ({
  day_number: n,
  title: `Title ${n.toString()}`,
  estimated_cost: null,
  activities: [
    act(`Act ${n.toString()}`, "morning"),
    act(`Lunch ${n.toString()}`, "afternoon"),
    act(`Walk ${n.toString()}`, "afternoon"),
    act(`Free ${n.toString()}`, null),
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
  match_reasoning: "Fits the beach budget.",
  daily_itinerary: [day(1), day(2), day(3)],
} as unknown as Itinerary;

async function open() {
  render(<OptionCard option={option} />);
  await userEvent.click(screen.getByRole("button", { name: "Day-by-day" }));
  return screen.findByRole("dialog");
}

const isCurrent = (dialog: HTMLElement, n: number) =>
  within(dialog)
    .getByRole("button", { name: `Day ${n.toString()}` })
    .getAttribute("aria-current") === "step";

describe("OptionCard day-by-day", () => {
  it("opens on day 1 and steps with Next/Previous", async () => {
    const dialog = await open();
    expect(within(dialog).getByText("Day 1 of 3")).toBeInTheDocument();
    expect(isCurrent(dialog, 1)).toBe(true);
    expect(within(dialog).getByRole("button", { name: "Previous day" })).toHaveAttribute(
      "aria-disabled",
      "true"
    );
    await userEvent.click(within(dialog).getByRole("button", { name: "Next day" }));
    expect(within(dialog).getByText("Day 2 of 3")).toBeInTheDocument();
    expect(within(dialog).getByText("Act 2")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Previous day" }));
    expect(isCurrent(dialog, 1)).toBe(true);
  });

  it("keeps focus on Next after reaching the last day", async () => {
    const dialog = await open();
    await userEvent.click(within(dialog).getByRole("button", { name: "Day 2" }));
    const next = within(dialog).getByRole("button", { name: "Next day" });
    await userEvent.click(next);
    expect(isCurrent(dialog, 3)).toBe(true);
    // jsdom doesn't blur an element that becomes `disabled`, so assert the attributes too.
    expect(next).toBeEnabled();
    expect(next).toHaveAttribute("aria-disabled", "true");
    expect(document.activeElement).toBe(next);
  });

  it("jumps to a day from the strip", async () => {
    const dialog = await open();
    await userEvent.click(within(dialog).getByRole("button", { name: "Day 3" }));
    expect(isCurrent(dialog, 3)).toBe(true);
    expect(isCurrent(dialog, 1)).toBe(false);
    expect(within(dialog).getByText("Act 3")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Next day" })).toHaveAttribute(
      "aria-disabled",
      "true"
    );
  });

  it("prints a slot label once per run of equal slots, and none for null", async () => {
    const dialog = await open();
    expect(within(dialog).getAllByText("morning")).toHaveLength(1);
    expect(within(dialog).getAllByText("afternoon")).toHaveLength(1);
    // The null stop's title row holds only the title.
    expect(within(dialog).getByText("Free 1").nextElementSibling).toBeNull();
  });

  it("shows match_reasoning on the card, not in the dialog", async () => {
    const dialog = await open();
    expect(screen.getByText("Fits the beach budget.")).toBeInTheDocument();
    expect(within(dialog).queryByText("Fits the beach budget.")).not.toBeInTheDocument();
  });

  it("moves with ArrowRight/ArrowLeft and clamps at the ends", async () => {
    const dialog = await open();
    await userEvent.keyboard("{ArrowLeft}");
    expect(isCurrent(dialog, 1)).toBe(true);
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(isCurrent(dialog, 3)).toBe(true);
    expect(within(dialog).getByRole("button", { name: "Next day" })).toHaveAttribute(
      "aria-disabled",
      "true"
    );
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(isCurrent(dialog, 2)).toBe(true);
  });

  it("handles arrow keys that the dialog stops from bubbling", async () => {
    const dialog = await open();
    dialog.addEventListener("keydown", (e) => {
      e.stopPropagation();
    });
    fireEvent.keyDown(within(dialog).getByRole("button", { name: "Next day" }), {
      key: "ArrowRight",
    });
    expect(isCurrent(dialog, 2)).toBe(true);
  });
});
