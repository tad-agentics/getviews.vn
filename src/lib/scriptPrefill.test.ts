import { describe, expect, it } from "vitest";
import { scriptPrefillFromChannel, scriptPrefillFromRitual, scriptPrefillFromVideo } from "./scriptPrefill";

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
