import { describe, expect, it } from "vitest";

import {
  DEEP_ONLY_SECTION_LABELS_VI,
  labelForLockedSection,
  lockedSectionSubtitle,
  normalizeLockedSectionTeasers,
  shouldShowDeepUpsell,
} from "./videoDeepUpsell";

describe("videoDeepUpsell", () => {
  it("labelForLockedSection prefers BE title_vi", () => {
    expect(labelForLockedSection("sound", "Âm thanh tùy chỉnh")).toBe("Âm thanh tùy chỉnh");
  });

  it("labelForLockedSection falls back to §4.2 map", () => {
    expect(labelForLockedSection("sound", "")).toBe(DEEP_ONLY_SECTION_LABELS_VI.sound);
  });

  it("normalizeLockedSectionTeasers dedupes and labels rows", () => {
    expect(
      normalizeLockedSectionTeasers([
        { section_id: "sound", title_vi: "" },
        { section_id: "sound", title_vi: "dup" },
        { section_id: "editing", title_vi: "Chỉnh sửa", signal_count: 2 },
      ]),
    ).toEqual([
      { section_id: "sound", title_vi: DEEP_ONLY_SECTION_LABELS_VI.sound! },
      { section_id: "editing", title_vi: "Chỉnh sửa", signal_count: 2 },
    ]);
  });

  it("lockedSectionSubtitle prefers teaser_vi then signal_count", () => {
    expect(
      lockedSectionSubtitle({
        section_id: "boost_attribution",
        title_vi: "Boost",
        signal_count: 2,
        teaser_vi: "Kiểm tra phân phối bất thường",
      }),
    ).toBe("Kiểm tra phân phối bất thường");
    expect(
      lockedSectionSubtitle({
        section_id: "sound",
        title_vi: "Âm thanh",
        signal_count: 3,
      }),
    ).toBe("+3 nhận định");
    expect(
      lockedSectionSubtitle({ section_id: "sound", title_vi: "Âm thanh" }),
    ).toBeNull();
  });

  it("shouldShowDeepUpsell is true only for basic depth", () => {
    expect(shouldShowDeepUpsell("basic", undefined)).toBe(true);
    expect(shouldShowDeepUpsell("deep", undefined)).toBe(false);
    expect(shouldShowDeepUpsell("basic", "deep")).toBe(false);
    expect(shouldShowDeepUpsell(null, "basic")).toBe(true);
  });
});
