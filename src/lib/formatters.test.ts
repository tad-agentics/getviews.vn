import { describe, expect, it } from "vitest";
import {
  formatViews,
  formatVN,
  formatRecencyVI,
  formatBreakoutVI,
} from "./formatters";

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

describe("formatVN", () => {
  it("formats a 7-digit number with Vietnamese dot separators", () => {
    // Uses en-US toLocaleString then swaps commas → dots: 1,234,567 → 1.234.567
    expect(formatVN(1_234_567)).toBe("1.234.567");
  });

  it("formats a 5-digit number", () => {
    expect(formatVN(46_000)).toBe("46.000");
  });

  it("rounds floating-point input before formatting", () => {
    expect(formatVN(1_234.6)).toBe("1.235");
  });

  it("formats a 3-digit number with no separator", () => {
    expect(formatVN(999)).toBe("999");
  });
});

describe("formatRecencyVI", () => {
  it("returns 'Hôm nay' for 0 days ago", () => {
    expect(formatRecencyVI(0)).toBe("Hôm nay");
  });

  it("returns 'Hôm qua' for 1 day ago", () => {
    expect(formatRecencyVI(1)).toBe("Hôm qua");
  });

  it("returns '3 ngày trước' for 3 days ago", () => {
    expect(formatRecencyVI(3)).toBe("3 ngày trước");
  });

  it("returns '7 ngày trước' for exactly 7 days ago (boundary — still in daily range)", () => {
    // daysAgo <= 7 → "${daysAgo} ngày trước"; 'Tuần trước' starts at 8
    expect(formatRecencyVI(7)).toBe("7 ngày trước");
  });

  it("returns 'Tuần trước' for 8 days ago (first day of weekly range)", () => {
    expect(formatRecencyVI(8)).toBe("Tuần trước");
  });

  it("returns 'Tuần trước' for 14 days ago (last day of weekly range)", () => {
    expect(formatRecencyVI(14)).toBe("Tuần trước");
  });

  it("returns '3 tuần trước' for 21 days ago", () => {
    expect(formatRecencyVI(21)).toBe("3 tuần trước");
  });

  it("returns '1 tháng trước' for 31 days ago", () => {
    expect(formatRecencyVI(31)).toBe("1 tháng trước");
  });
});

describe("formatBreakoutVI", () => {
  it("formats a decimal ratio with Vietnamese comma separator and x suffix", () => {
    expect(formatBreakoutVI(3.5)).toBe("3,5x");
  });

  it("formats a whole number ratio with one decimal place", () => {
    expect(formatBreakoutVI(2)).toBe("2,0x");
  });

  it("formats a ratio less than 1", () => {
    expect(formatBreakoutVI(0.8)).toBe("0,8x");
  });
});
