/**
 * Live audit 2026-06-12 — chip "0.7× TB FORMAT" vs KPI "0.6× ngách"
 * mismatch. tier_ratio (when present) is the single source of truth for
 * the VIEW KPI delta.
 */
import { describe, expect, it } from "vitest";

import type { VideoKpi } from "@/lib/api-types";
import { formatTierRatio, reconcileViewKpiWithTierRatio } from "./videoKpis";

const kpis: VideoKpi[] = [
  { label: "VIEW", value: "64K", delta: "0.6× ngách" },
  { label: "GIỮ CHÂN", value: "55%", delta: "ngách TB" },
  { label: "SAVE RATE", value: "1.2%", delta: "khá" },
];

describe("reconcileViewKpiWithTierRatio", () => {
  it("replaces the VIEW ratio delta with tier_ratio when present", () => {
    const out = reconcileViewKpiWithTierRatio(kpis, 0.7);
    expect(out[0].delta).toBe("0.7× TB format");
    // Other KPIs untouched.
    expect(out[1]).toEqual(kpis[1]);
    expect(out[2]).toEqual(kpis[2]);
  });

  it("replaces the sparse-cohort '—' placeholder too", () => {
    const out = reconcileViewKpiWithTierRatio(
      [{ label: "VIEW", value: "64K", delta: "—" }],
      1.4,
    );
    expect(out[0].delta).toBe("1.4× TB format");
  });

  it("keeps the BE delta when tier_ratio is missing/invalid", () => {
    expect(reconcileViewKpiWithTierRatio(kpis, null)[0].delta).toBe("0.6× ngách");
    expect(reconcileViewKpiWithTierRatio(kpis, undefined)[0].delta).toBe("0.6× ngách");
    expect(reconcileViewKpiWithTierRatio(kpis, 0)[0].delta).toBe("0.6× ngách");
    expect(reconcileViewKpiWithTierRatio(kpis, Number.NaN)[0].delta).toBe("0.6× ngách");
  });

  it("does not clobber an unrelated VIEW annotation", () => {
    const out = reconcileViewKpiWithTierRatio(
      [{ label: "VIEW", value: "64K", delta: "top 5%" }],
      0.7,
    );
    expect(out[0].delta).toBe("top 5%");
  });

  it("formats like the PerformanceTierChip (1 decimal, integer ≥10×)", () => {
    expect(formatTierRatio(0.66)).toBe("0.7×");
    expect(formatTierRatio(2.5)).toBe("2.5×");
    expect(formatTierRatio(12.4)).toBe("12×");
  });
});
