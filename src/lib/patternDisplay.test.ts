import { describe, expect, it } from "vitest";

import {
  normalizeHookPhrase,
  pickPatternExample,
  pickPatternFormula,
  pickPatternHeadline,
} from "./patternDisplay";
import type { TopPattern } from "@/hooks/useTopPatterns";

const base: TopPattern = {
  id: "p1",
  display_name: "Gợi tò mò + quay dài + mặt người",
  weekly_instance_count: 5,
  weekly_instance_count_prev: 0,
  niche_video_count: 3,
  instance_count: 10,
  niche_spread: [4],
  avg_views: 800_000,
  lift_vs_niche: 1.5,
  sample_hook: "none",
  sample_creator_handle: "miule",
  videos: [],
  tier: "strong",
  structure: ["Hook: Cận mặt + hỏi thẳng về triệu chứng lạ"],
  why: null,
  careful: null,
  angles: null,
};

describe("patternDisplay", () => {
  it("normalizeHookPhrase rejects none/null placeholders", () => {
    expect(normalizeHookPhrase("none")).toBeNull();
    expect(normalizeHookPhrase("  NONE  ")).toBeNull();
    expect(normalizeHookPhrase("Miu Lê từng gây lo lắng")).toBe("Miu Lê từng gây lo lắng");
  });

  it("pickPatternHeadline prefers structure hook over display_name bucket", () => {
    expect(pickPatternHeadline(base)).toBe("Cận mặt + hỏi thẳng về triệu chứng lạ");
  });

  it("pickPatternFormula keeps taxonomy label when descriptive", () => {
    expect(pickPatternFormula(base)).toBe("Gợi tò mò + quay dài + mặt người");
  });

  it("pickPatternFormula enriches vague bucket names from deck hook", () => {
    expect(
      pickPatternFormula({
        ...base,
        display_name: "Cận",
        structure: ["Cận mặt sản phẩm + zoom chậm"],
      }),
    ).toBe("Cận mặt sản phẩm + zoom chậm");
  });

  it("pickPatternExample skips invalid hook and falls back to creator", () => {
    expect(pickPatternExample(base)).toBe("Video @miule");
  });
});
