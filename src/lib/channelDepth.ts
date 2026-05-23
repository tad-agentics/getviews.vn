/** F4/F5 channel analysis depth — §5.1 feature-map-v1. */
export type ChannelDepth = "nhanh" | "sau";

export const CHANNEL_SAU_CREDIT_COST = 3;

export function parseChannelDepth(raw: string | null): ChannelDepth {
  return raw === "sau" ? "sau" : "nhanh";
}

export function channelDepthCreditCost(depth: ChannelDepth): number {
  return depth === "sau" ? CHANNEL_SAU_CREDIT_COST : 0;
}
