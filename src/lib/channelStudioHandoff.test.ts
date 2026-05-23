import { describe, expect, it } from "vitest";

import {
  buildChannelStudioPath,
  channelRouteRedirectPath,
} from "./channelStudioHandoff";

describe("channelStudioHandoff", () => {
  it("buildChannelStudioPath encodes handle and depth", () => {
    expect(buildChannelStudioPath({ handle: "@foo", depth: "sau" })).toBe(
      "/app?handle=foo&depth=sau",
    );
  });

  it("channelRouteRedirectPath preserves legacy channel query params", () => {
    const params = new URLSearchParams("handle=bar&depth=sau&video_url=https%3A%2F%2Fx&force_refresh=1");
    expect(channelRouteRedirectPath(params)).toBe(
      "/app?handle=bar&depth=sau&video_url=https%3A%2F%2Fx&force_refresh=1",
    );
  });
});
