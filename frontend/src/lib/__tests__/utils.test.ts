import { describe, it, expect } from "vitest";
import { cn, parseJson } from "../utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes (falsy values ignored)", () => {
    const cond = false as boolean;
    expect(cn("base", cond && "cond", "end")).toBe("base end");
  });

  it("deduplicates conflicting Tailwind classes (last wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });

  it("handles undefined and null gracefully", () => {
    expect(cn("base", undefined, null, "extra")).toBe("base extra");
  });
});

describe("parseJson", () => {
  it("parses a valid JSON array", () => {
    expect(parseJson<number[]>("[1,2,3]", [])).toEqual([1, 2, 3]);
  });

  it("parses a valid JSON object", () => {
    expect(parseJson<{ a: number }>('{"a":1}', { a: 0 })).toEqual({ a: 1 });
  });

  it("returns fallback on invalid JSON", () => {
    expect(parseJson<number[]>("not json", [])).toEqual([]);
  });

  it("returns fallback on empty string", () => {
    expect(parseJson<string>("", "default")).toBe("default");
  });

  it("parses JSON null as null (not fallback)", () => {
    expect(parseJson<null>("null", null)).toBeNull();
  });
});
