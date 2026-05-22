import { describe, expect, it } from "vitest";
import {
  deltaPctFromVelocity,
  isSignalEligible,
  pickMorningSignals,
  sortSignalRows,
  type ClassMorningSignal,
} from "@/lib/classMorningSignals";
import type { ContentClassIntelligenceRow } from "@/hooks/useContentClassIntelligence";

function row(partial: Partial<ContentClassIntelligenceRow> & { content_class_id: number }): ContentClassIntelligenceRow {
  return {
    sample_size: 40,
    claim_tier: "moderate",
    video_count_7d: 12,
    avg_views_prior_7d: 1000,
    video_count_prior_7d: 8,
    view_velocity: 1.34,
    format_momentum: 1.5,
    lifecycle_stage: "emerging",
    ...partial,
  };
}

describe("new_class lifecycle", () => {
  it("assigns new_class when prior_7d is zero", () => {
    const r = row({
      content_class_id: 99,
      lifecycle_stage: "new_class",
      avg_views_prior_7d: 0,
      video_count_prior_7d: 0,
      view_velocity: null,
      format_momentum: null,
    });
    expect(r.lifecycle_stage).toBe("new_class");
    expect(isSignalEligible(r)).toBe(true);
  });

  it("surfaces new_class in opportunity slot before emerging", () => {
    const labels = new Map<number, string>([
      [1, "Skincare tutorial"],
      [2, "Review quán"],
    ]);
    const signals = pickMorningSignals(
      [
        row({ content_class_id: 2, lifecycle_stage: "emerging", view_velocity: 2.0 }),
        row({
          content_class_id: 1,
          lifecycle_stage: "new_class",
          avg_views_prior_7d: 0,
          video_count_prior_7d: 0,
          view_velocity: null,
        }),
      ],
      labels,
      new Set(),
    );
    expect(signals).toHaveLength(1);
    expect(signals[0]?.signal_type).toBe("new_class");
    expect(signals[0]?.delta_pct).toBeNull();
  });

  it("sorts new_class before emerging by lifecycle rank", () => {
    const sorted = sortSignalRows([
      row({ content_class_id: 2, lifecycle_stage: "emerging" }),
      row({ content_class_id: 1, lifecycle_stage: "new_class", avg_views_prior_7d: 0 }),
    ]);
    expect(sorted[0]?.content_class_id).toBe(1);
  });
});

describe("deltaPctFromVelocity", () => {
  it("returns null for new_class path", () => {
    expect(deltaPctFromVelocity(null)).toBeNull();
    expect(deltaPctFromVelocity(0)).toBeNull();
  });

  it("computes percent uplift", () => {
    expect(deltaPctFromVelocity(1.34)).toBe(34);
  });
});

describe("pickMorningSignals Max-2-Card", () => {
  it("caps at two cards (opportunity + defensive)", () => {
    const labels = new Map([[1, "A"], [2, "B"], [3, "C"]]);
    const signals: ClassMorningSignal[] = pickMorningSignals(
      [
        row({ content_class_id: 1, lifecycle_stage: "growing" }),
        row({ content_class_id: 2, lifecycle_stage: "declining", format_momentum: 0.6 }),
        row({ content_class_id: 3, lifecycle_stage: "declining", format_momentum: 0.5 }),
      ],
      labels,
      new Set(),
    );
    expect(signals.length).toBeLessThanOrEqual(2);
    expect(signals.some((s) => s.signal_type === "growing")).toBe(true);
    expect(signals.some((s) => s.signal_type === "declining")).toBe(true);
  });

  it("excludes thin claim_tier", () => {
    const signals = pickMorningSignals(
      [row({ content_class_id: 1, claim_tier: "thin", sample_size: 5 })],
      new Map([[1, "Thin"]]),
      new Set(),
    );
    expect(signals).toHaveLength(0);
  });

  it("low energy mode filters to low-friction format_axis only", () => {
    const axes = new Map<number, string>([
      [1, "vlog_daily"],
      [2, "montage_highlights"],
    ]);
    const signals = pickMorningSignals(
      [
        row({ content_class_id: 1, lifecycle_stage: "growing" }),
        row({ content_class_id: 2, lifecycle_stage: "emerging", view_velocity: 3 }),
      ],
      new Map([
        [1, "Vlog"],
        [2, "Montage"],
      ]),
      new Set(),
      { energyMode: "low", formatAxisByClassId: axes },
    );
    expect(signals).toHaveLength(1);
    expect(signals[0]?.content_class_id).toBe(1);
  });
});
