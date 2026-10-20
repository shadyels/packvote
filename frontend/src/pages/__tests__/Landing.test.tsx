import { describe, it, expect, vi, afterEach } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Landing from "../Landing";
import { runoff } from "@/components/DeparturesBoard";

const { auth } = vi.hoisted(() => ({ auth: { isAuthenticated: false } }));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => auth }));

const chips = (row: HTMLElement) => row.querySelectorAll("[data-chip-id]");

const setup = (isAuthenticated: boolean) => {
  auth.isAuthenticated = isAuthenticated;
  return render(
    <MemoryRouter>
      <Landing />
    </MemoryRouter>
  );
};

describe("Landing", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("anonymous: plan and join CTAs", () => {
    setup(false);
    expect(screen.getAllByRole("link", { name: "Plan a trip" })[0]).toHaveAttribute(
      "href",
      "/login"
    );
    expect(screen.getAllByRole("link", { name: "Join with a code" })[0]).toHaveAttribute(
      "href",
      "/join"
    );
    expect(screen.queryByRole("link", { name: "Go to dashboard" })).toBeNull();
  });

  it("authenticated: dashboard CTA", () => {
    setup(true);
    expect(screen.getAllByRole("link", { name: "Go to dashboard" })[0]).toHaveAttribute(
      "href",
      "/dashboard"
    );
    expect(screen.queryByRole("link", { name: "Plan a trip" })).toBeNull();
  });

  it("board: Lisbon wins round two with 5, Naxos is eliminated", () => {
    setup(false);
    const table = screen.getByRole("table", { name: /sample trip/i });
    const lisbon = within(table).getByRole("row", { name: /lisbon/i });
    const cells = within(lisbon).getAllByRole("cell");
    expect(cells[2]).toHaveTextContent("5"); // R2
    expect(within(lisbon).getByText("BOARDING")).toBeInTheDocument();
    const naxos = within(table).getByRole("row", { name: /naxos/i });
    expect(within(naxos).getByText("ELIMINATED")).toBeInTheDocument();
  });

  it("reduced motion renders the final state with no replay", () => {
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("reduce") }));
    setup(false);
    expect(screen.queryByRole("button", { name: /replay/i })).toBeNull();
    const lisbon = screen.getByRole("row", { name: /lisbon/i });
    expect(lisbon.className).toContain("bg-accent");
    expect(chips(lisbon)).toHaveLength(5);
    expect(within(lisbon).getByText("BOARDING").closest(".opacity-0")).toBeNull();
  });

  it("runoff derives rounds, elimination and winner", () => {
    const r = runoff(
      [
        ["a", "b", "c"],
        ["a", "c", "b"],
        ["b", "a", "c"],
        ["c", "b", "a"],
        ["c", "b", "a"],
      ],
      ["a", "b", "c"]
    );
    expect(r.rounds.map((x) => x.counts)).toEqual([
      { a: 2, b: 1, c: 2 },
      { a: 3, c: 2 },
    ]);
    expect(r.rounds[0]?.eliminated).toBe("b");
    expect(r.winner).toBe("a");
  });

  it("runoff: full tie has no winner, no ballots has no winner", () => {
    const tie = runoff(
      [
        ["a", "b"],
        ["b", "a"],
      ],
      ["a", "b"]
    );
    expect(tie.winner).toBeNull();
    expect(tie.rounds).toHaveLength(1);
    expect(tie.rounds[0]?.eliminated).toBeNull();
    expect(runoff([], ["a", "b"])).toEqual({ rounds: [], winner: null });
    expect(runoff([["a"]], [])).toEqual({ rounds: [], winner: null });
  });

  it("exposes names and final voters as text", () => {
    setup(false);
    const row = screen.getByRole("row", { name: /lisbon/i });
    expect(within(row).getByRole("rowheader", { name: "Lisbon" })).toBeInTheDocument();
    expect(row).toHaveTextContent("EL, FT, GN, HO, IP");
  });

  it("has exactly one h1", () => {
    setup(false);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  describe("board sequence (fake timers)", () => {
    afterEach(() => {
      vi.useRealTimers();
      vi.restoreAllMocks();
    });
    const lisbonRow = () => screen.getByRole("row", { name: /lisbon/i });
    const advance = (ms: number) => {
      act(() => {
        vi.advanceTimersByTime(ms);
      });
    };

    it("reaches BOARDING with chips moved into Lisbon after 3000 ms", () => {
      vi.useFakeTimers();
      setup(false);
      expect(lisbonRow().className).not.toContain("bg-accent");
      expect(chips(lisbonRow())).toHaveLength(3);
      advance(3001);
      expect(lisbonRow().className).toContain("bg-accent");
      expect(chips(lisbonRow())).toHaveLength(5);
      expect(within(lisbonRow()).getByText("BOARDING").closest(".opacity-0")).toBeNull();
    });

    it("Replay restarts the sequence", () => {
      vi.useFakeTimers();
      setup(false);
      advance(3001);
      fireEvent.click(screen.getByRole("button", { name: /replay/i }));
      expect(lisbonRow().className).not.toContain("bg-accent");
      expect(chips(lisbonRow())).toHaveLength(3);
      advance(3001);
      expect(lisbonRow().className).toContain("bg-accent");
    });

    it("Replay mid-move still ends in the final state", () => {
      vi.useFakeTimers();
      setup(false);
      advance(1750);
      fireEvent.click(screen.getByRole("button", { name: /replay/i }));
      advance(3001);
      expect(lisbonRow().className).toContain("bg-accent");
      expect(chips(lisbonRow())).toHaveLength(5);
    });

    it("double Replay leaves a single clean run", () => {
      vi.useFakeTimers();
      setup(false);
      advance(1000);
      const btn = screen.getByRole("button", { name: /replay/i });
      fireEvent.click(btn);
      fireEvent.click(btn);
      expect(vi.getTimerCount()).toBe(5);
    });

    it("unmount mid-sequence clears timers and warns nothing", () => {
      vi.useFakeTimers();
      const err = vi.spyOn(console, "error").mockImplementation(() => undefined);
      const { unmount } = setup(false);
      advance(1300);
      unmount();
      expect(vi.getTimerCount()).toBe(0);
      advance(5000);
      expect(err).not.toHaveBeenCalled();
    });
  });
});
