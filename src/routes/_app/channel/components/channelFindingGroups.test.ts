import { describe, expect, it } from "vitest";

import {
  AUDIT_RINGS,
  findingsForRing,
  VONG0_PREFLIGHT_FINDING_IDS,
  VONG3_VIRAL_FINDING_IDS,
  VONG4_AUDIENCE_FINDING_IDS,
} from "./channelFindingGroups";

describe("channelFindingGroups audit rings", () => {
  it("covers all 13 channel finding ids across five rings without overlap", () => {
    const allIds = AUDIT_RINGS.flatMap((ring) => [...ring.findingIds]);
    expect(new Set(allIds).size).toBe(allIds.length);
    expect(allIds.length).toBe(13);
  });

  it("places compliance under Vòng 0 and saturation under Vòng 3", () => {
    expect(VONG0_PREFLIGHT_FINDING_IDS.has("channel_compliance_aggregate")).toBe(true);
    expect(VONG3_VIRAL_FINDING_IDS.has("channel_peer_format_saturation")).toBe(true);
    expect(VONG4_AUDIENCE_FINDING_IDS.has("channel_recent_vs_peak_er_drop")).toBe(true);
  });

  it("sorts ring findings by strength high → low", () => {
    const ring = AUDIT_RINGS.find((r) => r.id === "v2")!;
    const sorted = findingsForRing(ring, [
      { finding_id: "channel_format_entropy_high", teaser: "a", strength: "low" },
      { finding_id: "channel_persona_drift", teaser: "b", strength: "high" },
    ]);
    expect(sorted[0]!.strength).toBe("high");
  });
});
