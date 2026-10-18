import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Join from "../Join";

const { mockAccess, mockNavigate } = vi.hoisted(() => ({
  mockAccess: vi.fn(),
  mockNavigate: vi.fn(),
}));

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    constructor(
      public status: number,
      message: string
    ) {
      super(message);
    }
  }
  return { ApiError, participants: { accessByCode: mockAccess } };
});
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  useNavigate: () => mockNavigate,
}));

import { ApiError } from "@/lib/api";

const setup = async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <Join />
    </MemoryRouter>
  );
  await user.type(screen.getByLabelText(/trip code/i), " ab12cd ");
  await user.type(screen.getByLabelText(/pin/i), "12a34");
  await user.click(screen.getByRole("button", { name: "Join trip" }));
};

describe("Join", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends an uppercased trimmed code and navigates on success", async () => {
    mockAccess.mockResolvedValue({ token: "tok" });
    await setup();
    expect(mockAccess).toHaveBeenCalledWith("AB12CD", "1234");
    expect(mockNavigate).toHaveBeenCalledWith("/trip/tok");
  });

  it("shows the API error message", async () => {
    mockAccess.mockRejectedValue(new ApiError(429, "Too many attempts"));
    await setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many attempts");
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("maps 404 to the invalid code message", async () => {
    mockAccess.mockRejectedValue(new ApiError(404, "Not found"));
    await setup();
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid trip code or PIN");
  });
});
