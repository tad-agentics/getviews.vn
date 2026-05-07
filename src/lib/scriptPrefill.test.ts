import { describe, expect, it } from "vitest";
import {
  scriptPrefillFromChannel,
  scriptPrefillFromPattern,
  scriptPrefillFromRitual,
  scriptPrefillFromVideo,
} from "./scriptPrefill";

import type { TopPattern } from "@/hooks/useTopPatterns";

const ritualSample = {
  hook_type_en: "comparison",
  hook_type_vi: "So sánh",
  title_vi: "Test tiêu đề",
  why_works: "vì sao",
  retention_est_pct: 40,
  shot_count: 5,
  length_sec: 45,
};

describe("scriptPrefillFromRitual", () => {
  it("includes niche, topic, hook, duration", () => {
    const path = scriptPrefillFromRitual(ritualSample, 3);
    expect(path).toMatch(/^\/app\/script\?/);
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("niche_id")).toBe("3");
    expect(qs.get("topic")).toBe("Test tiêu đề");
    expect(qs.get("hook")).toBe("So sánh");
    expect(qs.get("duration")).toBe("45");
  });

  it("forwards sound_id + sound_name when ritual carries Sound Radar fields (L2.2 Sprint 3)", () => {
    const path = scriptPrefillFromRitual(
      {
        ...ritualSample,
        sound_id: "abc123",
        sound_name: "Hot Track",
        sound_velocity: "accelerating",
        sound_delta_pct: 200,
        urgency_band: "post_within_48h",
      },
      3,
    );
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("sound_id")).toBe("abc123");
    expect(qs.get("sound_name")).toBe("Hot Track");
  });

  it("omits sound_* params when fields are absent (pre-Sprint-3 ritual rows)", () => {
    const path = scriptPrefillFromRitual(ritualSample, 3);
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("sound_id")).toBeNull();
    expect(qs.get("sound_name")).toBeNull();
  });
});

describe("scriptPrefillFromChannel", () => {
  it("builds topic from channel name and passes top_hook", () => {
    const path = scriptPrefillFromChannel({
      niche_id: 2,
      name: "Creator X",
      handle: "creatorx",
      top_hook: "POV mở đầu",
    });
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("niche_id")).toBe("2");
    expect(qs.get("topic")).toContain("Creator X");
    expect(qs.get("hook")).toBe("POV mở đầu");
  });
});

describe("scriptPrefillFromPattern", () => {
  const patternSample = (overrides: Partial<TopPattern> = {}): TopPattern => ({
    id: "p1",
    display_name: "Hướng dẫn + mặt người",
    tier: "strong",
    weekly_instance_count: 12,
    weekly_instance_count_prev: 4,
    niche_video_count: 6,
    instance_count: 47,
    niche_spread: [3],
    avg_views: 200_000,
    lift_vs_niche: 2.4,
    sample_hook: "Mình dùng iPad Pro 6 tháng rồi và…",
    videos: [],
    structure: [
      "Mở: câu hỏi cá nhân (0-2s)",
      "Setup: bối cảnh dùng sản phẩm (2-6s)",
      "Body: 3 chi tiết bất ngờ (6-22s)",
      "Payoff: so sánh + CTA (22-30s)",
    ],
    why: "why",
    careful: "careful",
    angles: null,
    ...overrides,
  });

  it("uses structure[0] (Hook line) as topic, stripping the leading 'Mở:' / 'Hook:' tag", () => {
    const path = scriptPrefillFromPattern(patternSample(), 3);
    expect(path).toMatch(/^\/app\/script\?/);
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("niche_id")).toBe("3");
    expect(qs.get("topic")).toBe("câu hỏi cá nhân (0-2s)");
  });

  it("forwards sample_hook as the hook reference", () => {
    const path = scriptPrefillFromPattern(patternSample(), 3);
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("hook")).toBe("Mình dùng iPad Pro 6 tháng rồi và…");
  });

  it("falls back to display_name when structure is missing (defensive — filtered out by hook normally)", () => {
    const path = scriptPrefillFromPattern(
      patternSample({ structure: null }),
      3,
    );
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("topic")).toBe("Hướng dẫn + mặt người");
  });

  it("falls back to display_name as the hook when sample_hook is missing", () => {
    const path = scriptPrefillFromPattern(
      patternSample({ sample_hook: null }),
      3,
    );
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("hook")).toBe("Hướng dẫn + mặt người");
  });

  it("never sets a duration param (a pattern doesn't carry length_sec)", () => {
    const path = scriptPrefillFromPattern(patternSample(), 3);
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("duration")).toBeNull();
  });
});

describe("scriptPrefillFromVideo", () => {
  it("truncates long topic and sets duration", () => {
    const long = "x".repeat(600);
    const path = scriptPrefillFromVideo({
      niche_id: 1,
      topic: long,
      hook: "H1",
      duration_sec: 58.2,
    });
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect((qs.get("topic") ?? "").length).toBe(500);
    expect(qs.get("duration")).toBe("58");
  });

  it("omits niche_id when not provided", () => {
    const path = scriptPrefillFromVideo({
      topic: "Chủ đề",
      hook: null,
    });
    const qs = new URLSearchParams(path.split("?")[1]!);
    expect(qs.get("niche_id")).toBeNull();
    expect(qs.get("topic")).toBe("Chủ đề");
  });
});
