import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Ballot } from "../Ballot";
import type { Itinerary } from "@/types";

const opt = (id: number, name: string): Itinerary =>
  ({
    id,
    option_title: name,
    destination_name: name,
    daily_itinerary: [],
    total_estimated_budget: 1000,
    currency: "USD",
    highlights: [],
  }) as unknown as Itinerary;

const A = opt(1, "Alpha");
const B = opt(2, "Beta");
const C = opt(3, "Gamma");

const names = () => screen.getAllByRole("listitem").map((li) => li.textContent);

describe("Ballot", () => {
  it("reorders with move buttons, disables the ends, and submits the order", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<Ballot options={[A, B, C]} onSubmit={onSubmit} submitLabel="Submit vote" />);

    expect(screen.getByRole("button", { name: "Move Alpha up" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Move Gamma down" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Move Gamma up" }));
    expect(names()[1]).toContain("Gamma");
    expect(screen.getByRole("button", { name: "Move Gamma up" })).toHaveFocus();

    await user.click(screen.getByRole("button", { name: "Move Alpha down" }));
    await user.click(screen.getByRole("button", { name: "Submit vote" }));
    expect(onSubmit).toHaveBeenCalledWith([3, 1, 2]);
  });

  it("resets the order when the options change", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<Ballot options={[A, B]} onSubmit={vi.fn()} submitLabel="Go" />);
    await user.click(screen.getByRole("button", { name: "Move Beta up" }));
    expect(names()[0]).toContain("Beta");

    rerender(<Ballot options={[A, C]} onSubmit={vi.fn()} submitLabel="Go" />);
    expect(names()[0]).toContain("Alpha");
    expect(names()[1]).toContain("Gamma");
  });
});
