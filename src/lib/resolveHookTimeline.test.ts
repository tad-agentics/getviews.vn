import { describe, expect, it } from "vitest";

import { resolveHookTimeline } from "./resolveHookTimeline";

describe("resolveHookTimeline", () => {
  it("prefers top-level hook_timeline on answer-session payloads", () => {
    const top = [{ t: 0.2, event: "face_enter" as const }];
    const nested = [{ t: 1.0, event: "cut" as const }];
    expect(
      resolveHookTimeline({
        hook_timeline: top,
        user_video: { analysis: { hook_analysis: { hook_timeline: nested } } },
      }),
    ).toEqual(top);
  });

  it("falls back to nested chat extraction path", () => {
    const nested = [{ t: 0.8, event: "first_word" as const }];
    expect(
      resolveHookTimeline({
        user_video: { analysis: { hook_analysis: { hook_timeline: nested } } },
      }),
    ).toEqual(nested);
  });

  it("returns empty when no timeline present", () => {
    expect(resolveHookTimeline(null)).toEqual([]);
    expect(resolveHookTimeline({})).toEqual([]);
  });
});
