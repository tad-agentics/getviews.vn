/**
 * PR-T3 Trends — lifecycleHint pure helper test.
 */
import { describe, expect, it } from "vitest";

import { lifecycleHint } from "./patternLifecycle";

describe("lifecycleHint", () => {
  it("returns 'Hết sóng' + non-fresh when curr=0", () => {
    const r = lifecycleHint(0, 12);
    expect(r.text).toBe("Hết sóng");
    expect(r.isFresh).toBe(false);
  });

  it("returns 'Mới · tuần đầu' + fresh when prev=0 and curr>0", () => {
    const r = lifecycleHint(8, 0);
    expect(r.text).toBe("Mới · tuần đầu");
    expect(r.isFresh).toBe(true);
  });

  it("returns 'Đang lên' with growth pct when ratio ≥ 1.5", () => {
    const r = lifecycleHint(15, 10); // +50%
    expect(r.text).toBe("Đang lên · +50% tuần này");
    expect(r.isFresh).toBe(true);
  });

  it("returns 'Đang chậm lại' + non-fresh when ratio < 0.7", () => {
    const r = lifecycleHint(5, 12); // ~0.42
    expect(r.text).toBe("Đang chậm lại");
    expect(r.isFresh).toBe(false);
  });

  it("returns 'Đang sống' + fresh for neutral ratios (0.7 ≤ r < 1.5)", () => {
    expect(lifecycleHint(10, 10)).toEqual({ text: "Đang sống", isFresh: true });
    expect(lifecycleHint(8, 10)).toEqual({ text: "Đang sống", isFresh: true });
    expect(lifecycleHint(12, 10)).toEqual({ text: "Đang sống", isFresh: true });
  });

  it("0.7 boundary lands in 'Đang sống' (not 'Đang chậm lại')", () => {
    expect(lifecycleHint(7, 10)).toEqual({ text: "Đang sống", isFresh: true });
  });

  it("1.5 boundary lands in 'Đang lên' with the +50% suffix", () => {
    const r = lifecycleHint(15, 10);
    expect(r.text).toBe("Đang lên · +50% tuần này");
  });
});
