import { describe, it, expect } from "vitest";
import {
  STATUS,
  cn,
  daysBetween,
  flapText,
  formatDateRange,
  maxTripDays,
  parseDate,
  toISODate,
  tripStage,
} from "../trip";
import type { TripStatus } from "@/types";

const ALL_STATUSES: TripStatus[] = [
  "CREATED",
  "COLLECTING_PREFERENCES",
  "GENERATING",
  "GENERATION_FAILED",
  "VOTING",
  "FINALIZED",
];

describe("STATUS", () => {
  it("covers all 6 trip statuses with a label and tone", () => {
    expect(Object.keys(STATUS)).toHaveLength(6);
    for (const status of ALL_STATUSES) {
      expect(STATUS[status].label.length).toBeGreaterThan(0);
      expect(STATUS[status].tone.length).toBeGreaterThan(0);
    }
  });

  it.each([
    ["CREATED", "Created"],
    ["COLLECTING_PREFERENCES", "Collecting"],
    ["GENERATING", "Generating"],
    ["GENERATION_FAILED", "Failed"],
    ["VOTING", "Voting"],
    ["FINALIZED", "Finalized"],
  ] as [TripStatus, string][])("%s has label %s", (status, label) => {
    expect(STATUS[status].label).toBe(label);
  });
});

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("ignores falsy values", () => {
    const cond = false as boolean;
    expect(cn("base", cond && "cond", undefined, null, "end")).toBe("base end");
  });

  it("deduplicates conflicting Tailwind classes (last wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
});

describe("maxTripDays", () => {
  it.each([
    [1, 40],
    [2, 20],
    [3, 13],
    [5, 7],
  ])("numOptions=%i -> %i days", (n, days) => {
    expect(maxTripDays(n)).toBe(days);
  });

  it("is at least 1, even for invalid or huge option counts", () => {
    expect(maxTripDays(0)).toBe(1);
    expect(maxTripDays(-3)).toBe(1);
    expect(maxTripDays(1000)).toBe(1);
  });
});

describe("dates", () => {
  it("parseDate/toISODate round-trip as local calendar dates", () => {
    const d = parseDate("2025-06-01");
    expect(d.getFullYear()).toBe(2025);
    expect(d.getMonth()).toBe(5);
    expect(d.getDate()).toBe(1);
    expect(toISODate(d)).toBe("2025-06-01");
  });

  it("parses API datetimes (with or without Z) as the same calendar date", () => {
    for (const iso of ["2025-06-01T00:00:00", "2025-06-01T00:00:00Z"]) {
      expect(toISODate(parseDate(iso))).toBe("2025-06-01");
    }
    expect(daysBetween("2025-06-01T00:00:00", "2025-06-08T00:00:00")).toBe(7);
    expect(formatDateRange("2025-06-01T00:00:00", "2025-06-08T00:00:00")).toContain(" – ");
  });

  it("daysBetween counts calendar days (also across DST)", () => {
    expect(daysBetween("2025-06-01", "2025-06-08")).toBe(7);
    expect(daysBetween("2025-03-08", "2025-03-10")).toBe(2);
    expect(daysBetween("2025-06-01", "2025-06-01")).toBe(0);
  });

  it("formatDateRange handles each combination", () => {
    expect(formatDateRange(null, null)).toBeNull();
    expect(formatDateRange("2025-06-01", null)).toMatch(/^From /);
    expect(formatDateRange(null, "2025-06-08")).toMatch(/^Until /);
    expect(formatDateRange("2025-06-01", "2025-06-08")).toContain(" – ");
  });
});

describe("flapText", () => {
  it("keeps the part before the first comma", () => {
    expect(flapText("Naxos, Greece")).toBe("Naxos");
  });

  it("caps at 12 characters", () => {
    expect(flapText("Mediterranean coast")).toBe("Mediterranea");
  });

  it("falls back to the whole string when the head is empty", () => {
    expect(flapText(", Greece")).toBe(", Greece");
  });

  it("trims whitespace, including after the cap", () => {
    expect(flapText("  Naxos  , Greece")).toBe("Naxos");
    expect(flapText("Sri Lanka tour", 8)).toBe("Sri Lank");
    expect(flapText("Sri Lanka tour", 4)).toBe("Sri");
  });
});

describe("tripStage", () => {
  it.each([
    ["CREATED", 0, false],
    ["COLLECTING_PREFERENCES", 0, false],
    ["GENERATING", 1, false],
    ["GENERATION_FAILED", 1, true],
    ["VOTING", 2, false],
    ["FINALIZED", 3, false],
  ] as const)("%s -> index %i, failed %s", (status, index, failed) => {
    expect(tripStage(status)).toEqual({ index, failed });
  });
});
