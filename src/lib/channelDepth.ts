import type { AnswerHandoffDepth } from "./answerHandoff";

/** F4/F5 channel analysis depth — §5.1 feature-map-v1. */
export type ChannelDepth = "nhanh" | "sau";

export const CHANNEL_SAU_CREDIT_COST = 3;

/** Map composer / URL depth to internal channel depth. */
export function parseChannelDepth(raw: string | null): ChannelDepth {
  if (raw === "sau" || raw === "deep") return "sau";
  return "nhanh";
}

export function channelDepthFromHandoff(depth: AnswerHandoffDepth): ChannelDepth {
  return depth === "deep" ? "sau" : "nhanh";
}

export function channelDepthToHandoff(depth: ChannelDepth): AnswerHandoffDepth {
  return depth === "sau" ? "deep" : "basic";
}

export function channelDepthCreditCost(depth: ChannelDepth): number {
  return depth === "sau" ? CHANNEL_SAU_CREDIT_COST : 0;
}
