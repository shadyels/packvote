import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: false, isLoading: false, user: null, logout: vi.fn() }),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  auth: {},
}));
// Pages owned by other phases: stand-ins keep this test about routing only.
vi.mock("@/pages/Trip", () => ({ default: () => <p>trip page</p> }));
vi.mock("@/pages/Join", () => ({ default: () => <p>join page</p> }));
vi.mock("@/pages/Landing", () => ({ default: () => <p>landing page</p> }));
vi.mock("@/pages/TripDetail", () => ({ default: () => <p>trip detail page</p> }));

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

function at(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <App />
    </MemoryRouter>
  );
}

describe("routes", () => {
  it.each(["/join/abc", "/trip/abc", "/trip/abc/vote"])("%s renders the Trip page", (url) => {
    at(url);
    expect(screen.getByText("trip page")).toBeInTheDocument();
  });

  it("/reset-password renders ResetPassword", () => {
    at("/reset-password?token=x");
    expect(screen.getByRole("heading", { name: "Choose a new password" })).toBeInTheDocument();
  });

  it("unknown path renders NotFound", () => {
    at("/nope/nothing");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("/dashboard unauthenticated redirects to /login", () => {
    at("/dashboard");
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
