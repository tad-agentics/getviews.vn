import { describe, expect, it } from "vitest";

import { CHANNEL_CREDIT_COST, channelDepthCreditCost } from "./channelDepth";

describe("channelDepth", () => {
  it("channel analysis always costs 3 credits", () => {
    expect(CHANNEL_CREDIT_COST).toBe(3);
    expect(channelDepthCreditCost()).toBe(3);
  });
});
