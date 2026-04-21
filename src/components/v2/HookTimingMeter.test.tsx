/**
 * Phase D.1.6 — primitive render-test backfill (C.8.6 carryover).
 *
 * HookTimingMeter is a single-value horizontal bar showing the hook delay
 * against the 0.8–1.4s sweet-spot band. The cursor swaps colour based on
 * whether delay falls inside the band (benchmark blue) or outside
 * (`--gv-accent`).
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { HookTimingMeter } from "./HookTimingMeter";

afterEach(() => {
  cleanup();
});

describe("HookTimingMeter", () => {
  it("renders the 0s / 1s / 2s / 3s axis labels", () => {
    const { getByText } = render(<HookTimingMeter delayMs={1000} />);
    expect(getByText("0s")).toBeTruthy();
    expect(getByText("1s")).toBeTruthy();
    expect(getByText("2s")).toBeTruthy();
    expect(getByText("3s")).toBeTruthy();
  });

  it("places the cursor at the percentage corresponding to delayMs / 3000", () => {
    const { container } = render(<HookTimingMeter delayMs={1500} />);
    // The 3px cursor div sits on a computed `left: calc(50% - 1.5px)`.
    const cursor = container.querySelector(
      "div[style*='calc(50%']",
    ) as HTMLElement | null;
    expect(cursor).toBeTruthy();
  });

  it("colours the cursor benchmark blue when delay is inside the 0.8–1.4s band", () => {
    const { container } = render(<HookTimingMeter delayMs={1200} />);
    const cursor = container.querySelector(
      "div[style*='calc']",
    ) as HTMLElement | null;
    expect(cursor).toBeTruthy();
    // Inline style sets backgroundColor to `rgb(0, 159, 250)` for in-band delays.
    expect(cursor!.style.backgroundColor).toMatch(/rgb\(0,\s*159,\s*250\)/);
  });

  it("colours the cursor accent when delay is outside the sweet band", () => {
    const { container } = render(<HookTimingMeter delayMs={400} />);
    const cursor = container.querySelector(
      "div[style*='calc']",
    ) as HTMLElement | null;
    expect(cursor).toBeTruthy();
    expect(cursor!.style.backgroundColor).toMatch(/gv-accent/);
  });

  it("clamps the cursor position at 100% when delayMs exceeds 3000", () => {
    const { container } = render(<HookTimingMeter delayMs={9000} />);
    // cursor `left: calc(100% - 1.5px)` when pct is clamped.
    const cursor = container.querySelector(
      "div[style*='calc(100%']",
    ) as HTMLElement | null;
    expect(cursor).toBeTruthy();
  });
});
