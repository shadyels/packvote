import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../ProtectedRoute";

const auth = vi.hoisted(() => ({ value: { isLoading: false, isAuthenticated: false } }));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => auth.value }));

function renderRoute() {
  return render(
    <MemoryRouter initialEntries={["/secret"]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/secret" element={<p>secret</p>} />
        </Route>
        <Route path="/login" element={<p>login page</p>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("shows a skeleton and does not redirect while loading", () => {
    auth.value = { isLoading: true, isAuthenticated: false };
    renderRoute();
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByText("login page")).not.toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login", () => {
    auth.value = { isLoading: false, isAuthenticated: false };
    renderRoute();
    expect(screen.getByText("login page")).toBeInTheDocument();
  });

  it("renders the outlet when authenticated", () => {
    auth.value = { isLoading: false, isAuthenticated: true };
    renderRoute();
    expect(screen.getByText("secret")).toBeInTheDocument();
  });
});
