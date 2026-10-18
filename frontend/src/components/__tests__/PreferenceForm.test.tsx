import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreferenceForm } from "../PreferenceForm";

const { submit } = vi.hoisted(() => ({ submit: vi.fn() }));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  participants: { submitPreferences: submit },
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

beforeEach(() => {
  vi.clearAllMocks();
  submit.mockResolvedValue({});
});

function setup() {
  const onSubmitted = vi.fn();
  render(
    <PreferenceForm token="tok" proposedStart={null} proposedEnd={null} onSubmitted={onSubmitted} />
  );
  return onSubmitted;
}

const send = () => userEvent.click(screen.getByRole("button", { name: "Submit preferences" }));

describe("PreferenceForm", () => {
  it("rejects more than 20 activity tags without calling the API", async () => {
    setup();
    const tags = Array.from({ length: 21 }, (_, i) => `t${i.toString()}`).join(",");
    await userEvent.type(screen.getByLabelText("Activity tags"), tags);
    await send();
    expect(await screen.findByText(/Too many activity tags — max 20/)).toBeInTheDocument();
    expect(submit).not.toHaveBeenCalled();
  });

  it("rejects a minimum budget above the maximum without calling the API", async () => {
    setup();
    await userEvent.type(screen.getByLabelText("Budget min"), "900");
    await userEvent.type(screen.getByLabelText("Budget max"), "100");
    await send();
    expect(await screen.findByText(/Minimum budget can't exceed the maximum/)).toBeInTheDocument();
    expect(submit).not.toHaveBeenCalled();
  });

  it("accepts exactly 20 tags", async () => {
    setup();
    const tags = Array.from({ length: 20 }, (_, i) => `t${i.toString()}`).join(",");
    await userEvent.type(screen.getByLabelText("Activity tags"), tags);
    await send();
    expect(submit).toHaveBeenCalledTimes(1);
  });

  it("rejects a tag longer than 40 characters without calling the API", async () => {
    setup();
    await userEvent.type(screen.getByLabelText("Activity tags"), "x".repeat(41));
    await send();
    expect(await screen.findByText(/is too long — max 40 characters/)).toBeInTheDocument();
    expect(submit).not.toHaveBeenCalled();
  });

  it("submits empty fields as undefined", async () => {
    const onSubmitted = setup();
    await send();
    expect(submit).toHaveBeenCalledWith("tok", {
      name: undefined,
      preferred_start_date: undefined,
      preferred_end_date: undefined,
      budget_min: undefined,
      budget_max: undefined,
      currency: "USD",
      interests: undefined,
      activity_tags: undefined,
    });
    expect(onSubmitted).toHaveBeenCalled();
  });
});
