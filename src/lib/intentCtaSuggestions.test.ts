import { describe, expect, it } from "vitest";

import { getIntentCtaSuggestions, intentCtaQueryForSuggestion } from "./intentCtaSuggestions";

describe("intentCtaSuggestions", () => {
  const baseCtx = {
    format: "video" as const,
    mode: "win" as const,
    depth: "basic" as const,
    videoQuery: "https://www.tiktok.com/@a/video/1",
    scriptDraftId: null,
    evidenceVideoQuery: null,
    sessionInitialQ: "https://www.tiktok.com/@a/video/1",
    creatorHandle: null,
  };

  it("includes deep upgrade CTA for basic video", () => {
    const labels = getIntentCtaSuggestions(baseCtx).map((s) => s.label);
    expect(labels).toContain("Phân tích chuyên sâu (2 credit)");
  });

  it("omits deep CTA when depth is already deep", () => {
    const labels = getIntentCtaSuggestions({ ...baseCtx, depth: "deep" }).map((s) => s.id);
    expect(labels).not.toContain("video_deep");
  });

  it("disables compare when videoQuery missing", () => {
    const row = getIntentCtaSuggestions({ ...baseCtx, videoQuery: null }).find(
      (s) => s.id === "video_compare",
    );
    expect(row?.disabledReason).toBeTruthy();
  });

  it("includes Soi kênh pill on win when creatorHandle is present", () => {
    const row = getIntentCtaSuggestions({
      ...baseCtx,
      creatorHandle: "creatorx",
    }).find((s) => s.id === "video_channel");
    expect(row?.label).toBe("Soi kênh @creatorx");
    expect(row?.action).toBe("channel_handoff");
  });

  it("omits Soi kênh rail pill on flop (header CTA in VideoBody)", () => {
    const ids = getIntentCtaSuggestions({
      ...baseCtx,
      mode: "flop",
      creatorHandle: "creatorx",
    }).map((s) => s.id);
    expect(ids).not.toContain("video_channel");
  });

  it("keeps deep upgrade visible when video matrix exceeds four pills", () => {
    const suggestions = getIntentCtaSuggestions({
      ...baseCtx,
      creatorHandle: "creatorx",
    });
    expect(suggestions).toHaveLength(4);
    expect(suggestions.map((s) => s.id)).toContain("video_deep");
    expect(suggestions.map((s) => s.id)).not.toContain("video_compare");
  });

  it("intentCtaQueryForSuggestion returns fixed copy for script CTA", () => {
    const script = getIntentCtaSuggestions(baseCtx).find((s) => s.id === "video_script");
    expect(script).toBeTruthy();
    expect(intentCtaQueryForSuggestion(script!, baseCtx)).toContain("kịch bản");
  });
});
