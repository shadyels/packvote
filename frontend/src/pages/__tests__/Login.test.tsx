import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Login from "../Login";

const { mockLogin, mockRegister, mockReset, authState } = vi.hoisted(() => ({
  mockLogin: vi.fn(),
  mockRegister: vi.fn(),
  mockReset: vi.fn(),
  authState: { isAuthenticated: false },
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    isAuthenticated: authState.isAuthenticated,
    login: mockLogin,
    register: mockRegister,
  }),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  auth: { requestPasswordReset: mockReset },
}));

import { ApiError } from "@/lib/api";

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<p>dashboard page</p>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  authState.isAuthenticated = false;
});

describe("Login", () => {
  it("switches between sign in and register modes", async () => {
    const user = userEvent.setup();
    renderLogin();
    expect(screen.queryByLabelText(/^name/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Forgot password?" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /need an account/i }));
    expect(screen.getByLabelText(/^name/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Forgot password?" })).not.toBeInTheDocument();
  });

  it("shows the loading label, then navigates to the dashboard on success", async () => {
    let resolve: () => void = () => undefined;
    mockLogin.mockReturnValue(new Promise<void>((r) => (resolve = r)));
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText(/email/i), "a@b.co");
    await user.type(screen.getByLabelText(/password/i), "password1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("button", { name: "Signing in…" })).toBeDisabled();
    resolve();
    expect(await screen.findByText("dashboard page")).toBeInTheDocument();
    expect(mockLogin).toHaveBeenCalledWith("a@b.co", "password1");
  });

  it("shows the API error and clears it when the mode toggles", async () => {
    mockLogin.mockRejectedValue(new ApiError(401, "Invalid credentials"));
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText(/email/i), "a@b.co");
    await user.type(screen.getByLabelText(/password/i), "password1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");

    await user.click(screen.getByRole("button", { name: /need an account/i }));
    expect(screen.queryByText("Invalid credentials")).not.toBeInTheDocument();
  });

  it("redirects an authenticated user to the dashboard", () => {
    authState.isAuthenticated = true;
    renderLogin();
    expect(screen.getByText("dashboard page")).toBeInTheDocument();
  });

  it("forgot password shows non-revealing success copy", async () => {
    mockReset.mockResolvedValue({ message: "ok" });
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("button", { name: "Forgot password?" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(await screen.findByRole("textbox", { name: /email/i }), "x@y.co");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(dialog).toHaveTextContent("If that email is registered, a reset link has been sent.");
    });
    expect(mockReset).toHaveBeenCalledWith("x@y.co");
  });
});
