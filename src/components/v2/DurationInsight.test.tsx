/**
 * Phase D.1.6 — primitive render-test backfill (C.8.6 carryover).
 *
 * DurationInsight maps `durationSec` to one of four Vietnamese copy tiers:
 *   < 22    → "Ngắn — phù hợp hook thuần, ít dữ liệu"      (ink-4)
 *   22–40   → "★ Vùng vàng — 71% video thắng nằm đây"      (benchmark)
 *   41–60   → "Dài hơn TB — cần payoff rõ lúc 40s"          (ink-4)
 *   > 60    → "⚠ > 60s retention giảm 34%"                  (accent-deep)
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DurationInsight } from "./DurationInsight";

afterEach(() => {
  cleanup();
});

describe("DurationInsight", () => {
  it("renders the 'ngắn' tier for durationSec < 22", () => {
    const { getByText } = render(<DurationInsight durationSec={15} />);
    expect(getByText(/Ngắn — phù hợp hook thuần/)).toBeTruthy();
  });

  it("renders the sweet-spot tier for 22–40s inclusive with benchmark colour", () => {
    const { getByText } = render(<DurationInsight durationSec={28} />);
    const node = getByText(/Vùng vàng — 71% video thắng/);
    expect(node).toBeTruthy();
    expect(node.className).toMatch(/gv-chart-benchmark/);
  });

  it("tier boundary at exactly 22s lands in the sweet spot", () => {
    const { getByText } = render(<DurationInsight durationSec={22} />);
    expect(getByText(/Vùng vàng/)).toBeTruthy();
  });

  it("tier boundary at exactly 40s lands in the sweet spot", () => {
    const { getByText } = render(<DurationInsight durationSec={40} />);
    expect(getByText(/Vùng vàng/)).toBeTruthy();
  });

  it("tier boundary at 41s lands in the 'dài hơn TB' tier", () => {
    const { getByText } = render(<DurationInsight durationSec={41} />);
    expect(getByText(/Dài hơn TB/)).toBeTruthy();
  });

  it("tier boundary at > 60 flips to the warning tier with accent-deep colour", () => {
    const { getByText } = render(<DurationInsight durationSec={75} />);
    const node = getByText(/> 60s retention giảm 34%/);
    expect(node).toBeTruthy();
    expect(node.className).toMatch(/gv-accent-deep/);
  });
});
