import { describe, expect, it } from "vitest";

import {
  buildChannelStudioPath,
  studioHomeChannelRedirectPath,
} from "./channelStudioHandoff";

describe("channelStudioHandoff", () => {
  it("buildChannelStudioPath encodes handle and depth on /app/channel", () => {
    expect(buildChannelStudioPath({ handle: "@foo", depth: "deep" })).toBe(
      "/app/channel?handle=foo&depth=deep",
    );
    expect(buildChannelStudioPath({ handle: "bar", depth: "sau" })).toBe(
      "/app/channel?handle=bar&depth=deep",
    );
    expect(buildChannelStudioPath({ handle: "bar", depth: "basic" })).toBe(
      "/app/channel?handle=bar",
    );
  });

  it("studioHomeChannelRedirectPath preserves legacy /app?handle= params", () => {
    const params = new URLSearchParams(
      "handle=bar&depth=sau&video_url=https%3A%2F%2Fx&force_refresh=1",
    );
    expect(studioHomeChannelRedirectPath(params)).toBe(
      "/app/channel?handle=bar&depth=deep&video_url=https%3A%2F%2Fx&force_refresh=1",
    );
  });

  it("studioHomeChannelRedirectPath returns null without handle", () => {
    expect(studioHomeChannelRedirectPath(new URLSearchParams())).toBeNull();
  });
});
