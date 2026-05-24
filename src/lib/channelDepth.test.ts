import { describe, expect, it } from "vitest";

import { parseChannelDepth } from "./channelDepth";

describe("parseChannelDepth", () => {
  it("maps composer and legacy URL values", () => {
    expect(parseChannelDepth(null)).toBe("nhanh");
    expect(parseChannelDepth("basic")).toBe("nhanh");
    expect(parseChannelDepth("nhanh")).toBe("nhanh");
    expect(parseChannelDepth("deep")).toBe("sau");
    expect(parseChannelDepth("sau")).toBe("sau");
  });
});
