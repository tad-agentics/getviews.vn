import { describe, expect, it } from "vitest";
import {
  scriptPrefillFromChannel,
  scriptPrefillFromDeeplink,
  scriptPrefillFromPattern,
  scriptPrefillFromQueryParams,
  scriptPrefillFromRitual,
  scriptPrefillFromVideo,
} from "./scriptPrefill";

import type { TopPattern } from "@/hooks/useTopPatterns";

const ritualSample = {
  hook_type_en: "comparison",
  hook_type_vi: "So sánh",
  title_vi: "Test tiêu đề",
  why_works: "vì sao",
  shot_count: 5,
  length_sec: 45,
};

function parseAnswerQ(path: string): string {
  expect(path).toMatch(/^\/app\/answer\?/);
  const qs = new URLSearchParams(path.split("?")[1]!);
  const q = qs.get("q");
  expect(q).toBeTruthy();
  return decodeURIComponent(q!);
}

describe("scriptPrefillFromRitual", () => {
  it("includes topic, hook, duration in composer message", () => {
    const path = scriptPrefillFromRitual(ritualSample, 3);
    const msg = parseAnswerQ(path);
    expect(msg).toContain("Viết kịch bản TikTok");
    expect(msg).toContain("Test tiêu đề");
    expect(msg).toContain("So sánh");
    expect(msg).toContain("45");
  });

  it("forwards sound_name into composer text when ritual carries Sound Radar fields", () => {
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
    const msg = parseAnswerQ(path);
    expect(msg).toContain("Hot Track");
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
    const msg = parseAnswerQ(path);
    expect(msg).toContain("Creator X");
    expect(msg).toContain("POV mở đầu");
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

  it("uses structure[0] (Hook line) in message, stripping the leading 'Mở:' / 'Hook:' tag", () => {
    const path = scriptPrefillFromPattern(patternSample(), 3);
    const msg = parseAnswerQ(path);
    expect(msg).toContain("câu hỏi cá nhân (0-2s)");
  });

  it("embeds sample_hook in the message", () => {
    const path = scriptPrefillFromPattern(patternSample(), 3);
    const msg = parseAnswerQ(path);
    expect(msg).toContain("Mình dùng iPad Pro 6 tháng rồi và…");
  });

  it("falls back to display_name when structure is missing", () => {
    const path = scriptPrefillFromPattern(patternSample({ structure: null }), 3);
    const msg = parseAnswerQ(path);
    expect(msg).toContain("Hướng dẫn + mặt người");
  });

  it("falls back to display_name as hook text when sample_hook is missing", () => {
    const path = scriptPrefillFromPattern(patternSample({ sample_hook: null }), 3);
    const msg = parseAnswerQ(path);
    expect(msg).toContain("Góc hook: Hướng dẫn + mặt người");
  });
});

describe("scriptPrefillFromVideo", () => {
  it("truncates long topic and sets duration line", () => {
    const long = "x".repeat(600);
    const path = scriptPrefillFromVideo({
      niche_id: 1,
      topic: long,
      hook: "H1",
      duration_sec: 58.2,
    });
    const msg = parseAnswerQ(path);
    expect(msg.length).toBeLessThan(long.length + 100);
    expect(msg).toContain("x".repeat(100));
    expect(msg).toContain("58");
    expect(msg).toContain("H1");
  });

  it("works without niche_id", () => {
    const path = scriptPrefillFromVideo({
      topic: "Chủ đề",
      hook: null,
    });
    const msg = parseAnswerQ(path);
    expect(msg).toContain("Chủ đề");
  });
});

describe("scriptPrefillFromDeeplink", () => {
  it("composes topic, hook, duration from legacy script query", () => {
    const path = scriptPrefillFromDeeplink({
      topic: "Review tai nghe",
      hook: "So sánh 200k vs 2tr",
      duration_sec: 32,
    });
    expect(path).toMatch(/^\/app\/answer\?/);
    const msg = parseAnswerQ(path!);
    expect(msg).toContain("Review tai nghe");
    expect(msg).toContain("So sánh");
    expect(msg).toContain("32");
  });

  it("composes channel formula prefill", () => {
    const path = scriptPrefillFromDeeplink({
      prefill_handle: "minhreview",
      prefill_format: "POV unbox",
    });
    const msg = parseAnswerQ(path!);
    expect(msg).toContain("minhreview");
    expect(msg).toContain("POV unbox");
  });
});

describe("scriptPrefillFromQueryParams", () => {
  it("parses URLSearchParams from Douyin-style deeplink", () => {
    const params = new URLSearchParams();
    params.set("topic", "Douyin title");
    params.set("hook", "Sub VN");
    params.set("duration", "45");
    const path = scriptPrefillFromQueryParams(params);
    expect(path).toBeTruthy();
    const msg = parseAnswerQ(path!);
    expect(msg).toContain("Douyin title");
    expect(msg).toContain("Sub VN");
    expect(msg).toContain("45");
  });
});
