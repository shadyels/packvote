import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Landing from "../Landing";

const { auth } = vi.hoisted(() => ({ auth: { isAuthenticated: false } }));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => auth }));

const setup = (isAuthenticated: boolean) => {
  auth.isAuthenticated = isAuthenticated;
  return render(
    <MemoryRouter>
      <Landing />
    </MemoryRouter>
  );
};

describe("Landing", () => {
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

  it("hero frame is inert, hidden and renders real components", () => {
    setup(false);
    const frame = screen.getByTestId("hero-frame");
    expect(frame).toHaveAttribute("aria-hidden", "true");
    expect(frame).toHaveAttribute("inert");
    expect(within(frame).getByText("Summer with the crew")).toBeInTheDocument();
    expect(frame.querySelector('[data-move="1-down"]')).not.toBeNull();
  });

  it("has exactly one h1", () => {
    setup(false);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
