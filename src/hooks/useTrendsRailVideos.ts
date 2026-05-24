import { useQuery } from "@tanstack/react-query";
import {
  applyBrowsableCorpusFilter,
  applyVideoCorpusNicheFilter,
} from "@/lib/corpusNicheFilter";
import { supabase } from "@/lib/supabase";

import { pickRotatingBreakoutWindow } from "./useTopBreakouts";

/**
 * Trends sidebar / inline rail — curated recent breakouts in the user's
 * junction content classes (class-first browse scope), with legacy niche
 * fallback when junction is empty (parity with Home ``useTopBreakouts``).
 */

export type TrendsRailVideo = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string | null;
  tiktok_url: string | null;
  views: number;
  posted_at: string | null;
  indexed_at: string | null;
  hook_phrase: string | null;
  hook_type: string | null;
  breakout_multiplier: number | null;
  content_format: string | null;
};

export type TrendsRailMeta = {
  /** True when eligible pool was thin and unfiltered rows filled the rail. */
  usedFallback: boolean;
  /** Count from the eligible-only pass before merge. */
  eligibleCount: number;
};

export type TrendsRailPayload = {
  videos: TrendsRailVideo[];
  meta: TrendsRailMeta;
};

export type TrendsRailScope = {
  contentClassIds: number[];
  /** Legacy ``ingest_loop_niche_id`` when junction is empty. */
  legacyNicheId?: number | null;
};

const RAIL_LIMIT = 5;
const RAIL_POOL_LIMIT = 20;
const RAIL_COLS =
  "video_id, thumbnail_url, creator_handle, tiktok_url, views, posted_at, indexed_at, hook_phrase, hook_type, breakout_multiplier, content_format";

const RECENT_DAYS = 14;
const MIN_BREAKOUT = 1.0;
const TRENDS_RAIL_ROTATION_MS = 15 * 60 * 1000;
/** Offset from Home bucket so Tier III (3) and Trends (5) rarely show the same top rows. */
const TRENDS_RAIL_BUCKET_OFFSET = 3;

function applyTrendsRailScopeFilter<T extends { eq: (c: string, v: number) => T; in: (c: string, v: number[]) => T; not: (c: string, op: string, v: null) => T }>(
  query: T,
  scope: TrendsRailScope,
): T {
  if (scope.contentClassIds.length > 0) {
    return applyBrowsableCorpusFilter(
      applyVideoCorpusNicheFilter(query, { contentClassIds: scope.contentClassIds }),
    );
  }
  if (scope.legacyNicheId != null) {
    return applyBrowsableCorpusFilter(query.eq("ingest_loop_niche_id", scope.legacyNicheId));
  }
  return applyBrowsableCorpusFilter(query);
}

async function queryRailPool(
  since: string,
  scope: TrendsRailScope,
  limit: number,
  eligibleOnly: boolean,
): Promise<TrendsRailVideo[]> {
  let q = supabase
    .from("video_corpus")
    .select(RAIL_COLS)
    .gte("posted_at", since)
    .not("posted_at", "is", null)
    .gte("breakout_multiplier", MIN_BREAKOUT)
    .eq("language", "vi");
  if (eligibleOnly) {
    q = q.eq("reference_eligible", true);
  }
  q = applyTrendsRailScopeFilter(q, scope);
  const { data, error } = await q
    .order("breakout_multiplier", { ascending: false })
    .order("posted_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return (data ?? []) as TrendsRailVideo[];
}

function mergeEligibleFirst(
  eligible: TrendsRailVideo[],
  fallback: TrendsRailVideo[],
  poolLimit: number,
): TrendsRailVideo[] {
  const merged = [...eligible];
  const seen = new Set(merged.map((r) => r.video_id));
  for (const row of fallback) {
    if (seen.has(row.video_id)) continue;
    seen.add(row.video_id);
    merged.push(row);
    if (merged.length >= poolLimit) break;
  }
  return merged;
}

/** Eligible-first with thin fallback — exported for unit tests. */
export async function fetchTrendsRailBreakouts(
  scope: TrendsRailScope,
  limit = RAIL_LIMIT,
  nowMs = Date.now(),
): Promise<TrendsRailPayload> {
  const hasScope =
    scope.contentClassIds.length > 0 || scope.legacyNicheId != null;
  if (!hasScope) {
    return { videos: [], meta: { usedFallback: false, eligibleCount: 0 } };
  }

  const since = new Date(nowMs - RECENT_DAYS * 24 * 3600 * 1000).toISOString();

  const eligible = await queryRailPool(since, scope, RAIL_POOL_LIMIT, true);
  let pool = eligible;

  if (pool.length < RAIL_POOL_LIMIT) {
    const fallback = await queryRailPool(since, scope, RAIL_POOL_LIMIT, false);
    pool = mergeEligibleFirst(eligible, fallback, RAIL_POOL_LIMIT);
  }

  const eligibleIds = new Set(eligible.map((r) => r.video_id));
  const usedFallback = pool.some((r) => !eligibleIds.has(r.video_id));

  const videos = pickRotatingBreakoutWindow(
    pool,
    limit,
    nowMs,
    TRENDS_RAIL_ROTATION_MS,
    TRENDS_RAIL_BUCKET_OFFSET,
  );

  return {
    videos,
    meta: {
      usedFallback,
      eligibleCount: eligible.length,
    },
  };
}

export const trendsRailKeys = {
  byScope: (contentClassIds: number[], legacyNicheId: number | null) =>
    [
      "trends_rail_breakouts",
      [...contentClassIds].sort((a, b) => a - b),
      legacyNicheId,
    ] as const,
};

export function useTrendsRailVideos(scope: TrendsRailScope & { enabled?: boolean }) {
  const classIds = scope.contentClassIds;
  const legacyNicheId = scope.legacyNicheId ?? null;
  const hasScope = classIds.length > 0 || legacyNicheId != null;
  const enabled = scope.enabled !== false && hasScope;

  return useQuery<TrendsRailPayload>({
    queryKey: trendsRailKeys.byScope(classIds, legacyNicheId),
    queryFn: () =>
      fetchTrendsRailBreakouts({
        contentClassIds: classIds,
        legacyNicheId,
      }),
    enabled,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}

/** @deprecated Use TrendsRailPayload — kept for gradual test migration. */
export type RailVideo = TrendsRailVideo;

/** @deprecated Use TrendsRailPayload.videos — legacy two-rail shape removed. */
export type TrendsRailVideos = {
  breakouts7d: TrendsRailVideo[];
  virals: TrendsRailVideo[];
};
