import { describe, expect, it } from "vitest";

import type { VideoSegment } from "@/lib/api-types";
import { INFORMATIVE_STRUCTURE_SEGMENTS } from "@/lib/testFixtures/informativeStructureSegments";
import {
  buildStructureTimelineSummary,
  formatStructureTimeRange,
  isInformativeStructureTimeline,
  structureBeatLabelVi,
} from "./structureTimeline";

const informativeSegments: VideoSegment[] = [
  { name: "HOOK", pct: 22, color_key: "accent", start_sec: 0, end_sec: 13 },
  { name: "PROMISE", pct: 10, color_key: "ink-2", start_sec: 13, end_sec: 19 },
  { name: "APP 1", pct: 11, color_key: "ink-3", start_sec: 19, end_sec: 26 },
  { name: "APP 2", pct: 11, color_key: "ink-2", start_sec: 26, end_sec: 33 },
  { name: "APP 3", pct: 11, color_key: "ink-3", start_sec: 33, end_sec: 40 },
  { name: "APP 4", pct: 11, color_key: "ink-2", start_sec: 40, end_sec: 47 },
  { name: "APP 5", pct: 12, color_key: "ink-3", start_sec: 47, end_sec: 54 },
  { name: "CTA", pct: 12, color_key: "accent-deep", start_sec: 54, end_sec: 60 },
];

describe("structureTimeline", () => {
  it("maps beat names to Vietnamese", () => {
    expect(structureBeatLabelVi("HOOK")).toBe("Hook");
    expect(structureBeatLabelVi("APP 3")).toBe("Lý do 3");
  });

  it("formats time ranges for the bar cells", () => {
    expect(formatStructureTimeRange(0, 13)).toBe("0s–13s");
    expect(formatStructureTimeRange(54, 60)).toBe("54s–1:00");
  });

  it("rejects uniform bars even when timestamps exist (long clip noise)", () => {
    const uniform = INFORMATIVE_STRUCTURE_SEGMENTS.map((s) => ({ ...s, pct: 12 }));
    expect(isInformativeStructureTimeline(uniform)).toBe(false);
  });

  it("rejects uniform or template-only bars", () => {
    expect(isInformativeStructureTimeline(informativeSegments)).toBe(true);
    expect(
      isInformativeStructureTimeline([
        { name: "HOOK", pct: 13, color_key: "accent" },
        { name: "PROMISE", pct: 13, color_key: "ink-2", start_sec: 0, end_sec: 8 },
      ]),
    ).toBe(false);
    expect(
      isInformativeStructureTimeline(
        informativeSegments.map((s) => ({ ...s, pct: 12 })),
      ),
    ).toBe(false);
  });

  it("builds a pacing summary from hook vs body", () => {
    const summary = buildStructureTimelineSummary(informativeSegments, 60);
    expect(summary).toMatch(/Hook kéo dài/);
  });
});
