import type { VideoAnalyzeMeta, VideoAnalyzeMode } from "@/lib/api-types";

const CHANNEL_BREAKOUT_RATIO = 2;

function channelBreakoutFromMeta(meta: VideoAnalyzeMeta | undefined): boolean {
  if (!meta) return false;
  const ratio = meta.target_vs_creator_median;
  if (ratio != null && ratio >= CHANNEL_BREAKOUT_RATIO) return true;
  const median = meta.creator_median_views;
  const views = meta.views ?? 0;
  if (median == null || median <= 0 || views <= 0) return false;
  return views / median >= CHANNEL_BREAKOUT_RATIO;
}

/** True when the video should use win/breakout framing, not flop diagnosis. */
export function tierImpliesWinFraming(
  performanceTier: string | undefined,
  meta?: VideoAnalyzeMeta,
): boolean {
  const tier = (performanceTier ?? "").toLowerCase();
  if (tier === "hit") return true;
  if (tier === "flop") return false;
  return channelBreakoutFromMeta(meta);
}

export function tierIsGapHeavy(performanceTier: string | undefined): boolean {
  return (performanceTier ?? "").toLowerCase() === "flop";
}

export function tierIsStrengthHeavy(performanceTier: string | undefined): boolean {
  return (performanceTier ?? "").toLowerCase() === "hit";
}

export function maxFindingsForTier(performanceTier: string | undefined): number {
  const tier = (performanceTier ?? "unknown").toLowerCase();
  const map: Record<string, number> = {
    hit: 3,
    average: 4,
    flop: 6,
    early: 3,
    unknown: 4,
  };
  return map[tier] ?? map.unknown;
}

export function videoReportWasModeCorrected(
  reportMode: VideoAnalyzeMode | undefined,
  performanceTier: string | undefined,
  meta?: VideoAnalyzeMeta,
): boolean {
  return (
    (reportMode ?? "win") === "flop" && tierImpliesWinFraming(performanceTier, meta)
  );
}
