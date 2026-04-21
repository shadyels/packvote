import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "../AuthContext";

// ---------------------------------------------------------------------------
// Mock @/lib/api — use vi.hoisted so mocks are available in the factory
// ---------------------------------------------------------------------------

const { mockMe, mockLogin, mockRegister } = vi.hoisted(() => ({
  mockMe: vi.fn(),
  mockLogin: vi.fn(),
  mockRegister: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  auth: {
    me: mockMe,
    login: mockLogin,
    register: mockRegister,
  },
}));

// ---------------------------------------------------------------------------
// Helper component exposing AuthContext values via the DOM
// ---------------------------------------------------------------------------

function TestConsumer() {
  const { user, isLoading, isAuthenticated, login, logout, register } =
    useAuth();
  return (
    <div>
      <span data-testid="loading">{isLoading ? "loading" : "done"}</span>
      <span data-testid="authenticated">{isAuthenticated ? "yes" : "no"}</span>
      <span data-testid="user">{user ? user.email : "none"}</span>
      <button onClick={() => { void login("a@a.com", "pass"); }}>login</button>
      <button onClick={() => { void register("a@a.com", "pass"); }}>register</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

function Wrapped() {
  return (
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );
}

const FAKE_USER = {
  id: 1,
  email: "test@test.com",
  full_name: null,
  created_at: "2024-01-01",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AuthContext", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Use removeItem rather than clear() for wider env compatibility
    window.localStorage.removeItem("access_token");
  });

  it("unauthenticated when no token in localStorage", async () => {
    render(<Wrapped />);
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("done");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("no");
    expect(screen.getByTestId("user").textContent).toBe("none");
  });

  it("authenticated when token exists and me() succeeds", async () => {
    window.localStorage.setItem("access_token", "valid-token");
    mockMe.mockResolvedValue(FAKE_USER);

    render(<Wrapped />);
    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("yes");
    });
    expect(screen.getByTestId("user").textContent).toBe("test@test.com");
  });

  it("removes token and goes unauthenticated when me() fails", async () => {
    window.localStorage.setItem("access_token", "bad-token");
    mockMe.mockRejectedValue(new Error("Unauthorized"));

    render(<Wrapped />);
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("done");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("no");
    expect(window.localStorage.getItem("access_token")).toBeNull();
  });

  it("login stores token and sets user", async () => {
    mockLogin.mockResolvedValue({ access_token: "new-token", token_type: "bearer" });
    mockMe.mockResolvedValue(FAKE_USER);
    const user = userEvent.setup();

    render(<Wrapped />);
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("done");
    });

    await user.click(screen.getByText("login"));
    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("yes");
    });
    expect(window.localStorage.getItem("access_token")).toBe("new-token");
  });

  it("logout clears token and state", async () => {
    window.localStorage.setItem("access_token", "valid-token");
    mockMe.mockResolvedValue(FAKE_USER);
    const user = userEvent.setup();

    render(<Wrapped />);
    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("yes");
    });

    await user.click(screen.getByText("logout"));
    expect(screen.getByTestId("authenticated").textContent).toBe("no");
    expect(window.localStorage.getItem("access_token")).toBeNull();
  });

  it("register calls register → login → me in sequence", async () => {
    mockRegister.mockResolvedValue(FAKE_USER);
    mockLogin.mockResolvedValue({ access_token: "reg-token", token_type: "bearer" });
    mockMe.mockResolvedValue(FAKE_USER);
    const user = userEvent.setup();

    render(<Wrapped />);
    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("done");
    });

    await user.click(screen.getByText("register"));
    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("yes");
    });
    expect(mockRegister).toHaveBeenCalled();
    expect(mockLogin).toHaveBeenCalled();
    expect(mockMe).toHaveBeenCalled();
  });

  it("useAuth throws when used outside AuthProvider", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<TestConsumer />)).toThrow(
      "useAuth must be used within AuthProvider"
    );
    consoleError.mockRestore();
  });
});
