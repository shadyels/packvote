import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FlapWord, StatusFlap } from "../ui/Flap";

const tiles = (container: HTMLElement) =>
  Array.from(container.querySelectorAll<HTMLElement>('[aria-hidden="true"] > span'));

describe("FlapWord", () => {
  it("renders one aria-hidden tile per character with no animation on first render", () => {
    const { container } = render(<FlapWord text="ABC" size="sm" />);
    const t = tiles(container);
    expect(t.map((x) => x.textContent)).toEqual(["A", "B", "C"]);
    expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
    for (const x of t) expect(x).not.toHaveClass("animate-flip");
  });

  it("after a rerender, only the changed tile animates", () => {
    const { container, rerender } = render(<FlapWord text="ABC" size="sm" />);
    rerender(<FlapWord text="ABD" size="sm" />);
    expect(tiles(container).map((x) => x.classList.contains("animate-flip"))).toEqual([
      false,
      false,
      true,
    ]);
  });

  it("flip forces animation on mount", () => {
    const { container } = render(<FlapWord text="AB" size="sm" flip />);
    for (const x of tiles(container)) expect(x).toHaveClass("animate-flip");
  });

  it("default sr-only label equals the text", () => {
    render(<FlapWord text="Naxos" size="sm" />);
    expect(screen.getByText("Naxos")).toHaveClass("sr-only");
  });

  it("uses a custom label", () => {
    render(<FlapWord text="Naxos" size="sm" label="Destination Naxos" />);
    expect(screen.getByText("Destination Naxos")).toHaveClass("sr-only");
  });

  it("label={null} renders no sr-only text", () => {
    const { container } = render(<FlapWord text="Naxos" size="sm" label={null} />);
    expect(container.querySelector(".sr-only")).toBeNull();
  });
});

describe("StatusFlap", () => {
  it.each([
    ["muted", "bg-muted"],
    ["flap", "bg-flap"],
    ["success", "bg-success"],
    ["warning", "bg-warning"],
    ["danger", "bg-danger"],
  ] as const)("tone %s gets %s", (tone, cls) => {
    render(<StatusFlap tone={tone}>Label</StatusFlap>);
    expect(screen.getByText("Label")).toHaveClass(cls);
  });

  it("animates only when flip is set", () => {
    const { rerender } = render(<StatusFlap tone="success">X</StatusFlap>);
    expect(screen.getByText("X")).not.toHaveClass("animate-flip");
    rerender(
      <StatusFlap tone="success" flip>
        X
      </StatusFlap>
    );
    expect(screen.getByText("X")).toHaveClass("animate-flip");
  });
});
