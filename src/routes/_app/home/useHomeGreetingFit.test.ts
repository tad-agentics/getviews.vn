import { describe, expect, it } from "vitest";

/** Mirrors overflow ratio used by ``useHomeGreetingFit`` (exported for test only). */
function measureOverflowScale(containerWidth: number, scrollWidths: number[]): number {
  const MIN_SCALE = 0.55;
  let scale = 1;
  for (const sw of scrollWidths) {
    if (sw > containerWidth) scale = Math.min(scale, containerWidth / sw);
  }
  return Math.max(MIN_SCALE, Math.min(1, scale));
}

describe("useHomeGreetingFit scale math", () => {
  it("returns 1 when lines fit", () => {
    expect(measureOverflowScale(800, [600, 400])).toBe(1);
  });

  it("shrinks when the longest line overflows", () => {
    expect(measureOverflowScale(800, [1000, 400])).toBeCloseTo(0.8, 5);
  });

  it("respects minimum scale floor", () => {
    expect(measureOverflowScale(200, [1000, 900])).toBe(0.55);
  });
});
