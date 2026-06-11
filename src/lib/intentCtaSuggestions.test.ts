import { describe, expect, it } from "vitest";

import { getIntentCtaSuggestions, intentCtaQueryForSuggestion } from "./intentCtaSuggestions";

describe("intentCtaSuggestions", () => {
  const baseCtx = {
    format: "video" as const,
    mode: "win" as const,
    videoQuery: "https://www.tiktok.com/@a/video/1",
    scriptDraftId: null,
    evidenceVideoQuery: null,
    sessionInitialQ: "https://www.tiktok.com/@a/video/1",
    creatorHandle: null,
  };

  it("does not include deep upgrade CTA", () => {
    const ids = getIntentCtaSuggestions(baseCtx).map((s) => s.id);
    expect(ids).not.toContain("video_deep");
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

  it("intentCtaQueryForSuggestion returns empty for channel handoff", () => {
    const row = getIntentCtaSuggestions({
      ...baseCtx,
      creatorHandle: "creatorx",
    }).find((s) => s.id === "video_channel");
    expect(row).toBeTruthy();
    expect(intentCtaQueryForSuggestion(row!, baseCtx)).toBe("");
  });
});
