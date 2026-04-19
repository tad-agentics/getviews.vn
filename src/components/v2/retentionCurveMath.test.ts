import { describe, expect, it } from "vitest";
import { retentionDropAnnotations, VB_W } from "./retentionCurveMath";

const D60 = 60;

describe("retentionDropAnnotations", () => {
  it("returns empty for no-drop (too few points)", () => {
    expect(retentionDropAnnotations([{ t: 0, pct: 100 }], D60)).toEqual([]);
  });

  it("returns empty for flat curve (all steps below minDrop)", () => {
    const curve = [
      { t: 0, pct: 90 },
      { t: 30, pct: 89 },
      { t: 60, pct: 88 },
    ];
    expect(retentionDropAnnotations(curve, D60)).toEqual([]);
  });

  it("single steep drop yields one annotation", () => {
    const curve = [
      { t: 0, pct: 100 },
      { t: 30, pct: 100 },
      { t: 60, pct: 40 },
    ];
    const out = retentionDropAnnotations(curve, D60);
    expect(out).toHaveLength(1);
    expect(out[0].label).toMatch(/^drop −60% @/);
    expect(out[0].cx).toBeGreaterThanOrEqual(8);
    expect(out[0].cy).toBeGreaterThanOrEqual(12);
  });

  it("double-drop-close: second steepest within x-gap of first yields one label", () => {
    const curve = [
      { t: 0, pct: 100 },
      { t: 10, pct: 70 },
      { t: 20, pct: 40 },
    ];
    const out = retentionDropAnnotations(curve, D60);
    expect(out).toHaveLength(1);
    const tMax = 60;
    expect(Math.abs((15 / tMax) * VB_W - (5 / tMax) * VB_W)).toBeLessThan(VB_W / 5);
  });

  it("double-drop-far: two steep drops separated in x yield two labels", () => {
    const curve = [
      { t: 0, pct: 100 },
      { t: 20, pct: 55 },
      { t: 80, pct: 10 },
    ];
    const out = retentionDropAnnotations(curve, D60);
    expect(out).toHaveLength(2);
    expect(out[0].label).toMatch(/^drop −/);
    expect(out[1].label).toMatch(/^drop −/);
    expect(Math.abs(out[1].cx - out[0].cx)).toBeGreaterThan(0);
  });

  it("shifts second label down by 10 when cy would be within 8px of first", () => {
    const curve = [
      { t: 0, pct: 80 },
      { t: 24, pct: 22 },
      { t: 60, pct: 78 },
      { t: 100, pct: 24 },
    ];
    const out = retentionDropAnnotations(curve, 100);
    expect(out).toHaveLength(2);
    expect(out[1].cy - out[0].cy).toBeGreaterThanOrEqual(10);
  });
});
