import { describe, expect, it } from "vitest";
import { formatViews } from "./formatters";

describe("formatViews", () => {
  it("formats thousands with K suffix", () => {
    expect(formatViews(1500)).toBe("1.5K");
  });

  it("formats millions with M suffix", () => {
    expect(formatViews(2_300_000)).toBe("2.3M");
  });

  it("returns string for counts under 1000", () => {
    expect(formatViews(42)).toBe("42");
  });
});
