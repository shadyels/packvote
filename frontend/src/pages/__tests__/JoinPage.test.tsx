import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import JoinPage from "../JoinPage";
import { ApiError } from "@/lib/api";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.hoisted(() => vi.fn());
const mockAccessByCode = vi.hoisted(() => vi.fn());

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@/lib/api", () => ({
  participants: {
    accessByCode: mockAccessByCode,
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
      this.name = "ApiError";
    }
  },
}));

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderPage() {
  return render(
    <MemoryRouter>
      <JoinPage />
    </MemoryRouter>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("JoinPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders trip code and PIN inputs", () => {
    renderPage();
    expect(screen.getByLabelText(/trip code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/pin/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /join trip/i })
    ).toBeInTheDocument();
  });

  it("successful submit navigates to /trip/:token", async () => {
    mockAccessByCode.mockResolvedValue({
      token: "my-participant-token",
      participant: {},
    });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/trip code/i), "ABCD1234");
    await user.type(screen.getByLabelText(/pin/i), "5678");
    await user.click(screen.getByRole("button", { name: /join trip/i }));

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/trip/my-participant-token")
    );
  });

  it("sends uppercase trip code to the API", async () => {
    mockAccessByCode.mockResolvedValue({ token: "tok", participant: {} });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/trip code/i), "abcd1234");
    await user.type(screen.getByLabelText(/pin/i), "1234");
    await user.click(screen.getByRole("button", { name: /join trip/i }));

    await waitFor(() => expect(mockAccessByCode).toHaveBeenCalled());
    const [tripCode] = mockAccessByCode.mock.calls[0] as [string, string];
    expect(tripCode).toBe("ABCD1234");
  });

  it("shows friendly message on 404 error", async () => {
    mockAccessByCode.mockRejectedValue(new ApiError(404, "Not found"));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/trip code/i), "XXXX9999");
    await user.type(screen.getByLabelText(/pin/i), "0000");
    await user.click(screen.getByRole("button", { name: /join trip/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/invalid trip code or pin/i)
      ).toBeInTheDocument()
    );
  });

  it("shows generic error message on non-404 API error", async () => {
    mockAccessByCode.mockRejectedValue(new ApiError(500, "Server error"));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/trip code/i), "ABCD1234");
    await user.type(screen.getByLabelText(/pin/i), "1234");
    await user.click(screen.getByRole("button", { name: /join trip/i }));

    await waitFor(() =>
      expect(screen.getByText(/server error/i)).toBeInTheDocument()
    );
  });
});
