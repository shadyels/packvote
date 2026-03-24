import { describe, it, expect } from "vitest";
import { STATUS_CONFIG } from "../trip-status";
import type { TripStatus } from "@/types";

const ALL_STATUSES: TripStatus[] = [
  "CREATED",
  "COLLECTING_PREFERENCES",
  "GENERATING",
  "GENERATION_FAILED",
  "VOTING",
  "ITERATING",
  "FINALIZED",
];

describe("STATUS_CONFIG", () => {
  it("covers all 7 trip statuses", () => {
    expect(Object.keys(STATUS_CONFIG)).toHaveLength(7);
    for (const status of ALL_STATUSES) {
      expect(STATUS_CONFIG).toHaveProperty(status);
    }
  });

  it.each([
    ["CREATED", "Created"],
    ["COLLECTING_PREFERENCES", "Collecting"],
    ["GENERATING", "Generating"],
    ["GENERATION_FAILED", "Failed"],
    ["VOTING", "Voting"],
    ["ITERATING", "Iterating"],
    ["FINALIZED", "Finalized"],
  ] as [TripStatus, string][])(
    "%s has label %s",
    (status: TripStatus, label: string) => {
      expect(STATUS_CONFIG[status].label).toBe(label);
    }
  );

  it("each status has a non-empty className", () => {
    for (const status of ALL_STATUSES) {
      expect(STATUS_CONFIG[status].className.trim().length).toBeGreaterThan(0);
    }
  });
});
