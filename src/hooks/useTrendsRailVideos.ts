import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/**
 * Trends right-rail data hook (PR-T6).
 *
 * Two parallel ``video_corpus`` queries surfaced as a single payload:
 *   • ``breakouts7d`` — top 5 by ``breakout_multiplier`` in the trailing
 *     30 days (``posted_at`` window). Uses the batch-computed multiplier
 *     so videos are ranked relative to channel baseline, not raw views.
 *     Requires ``breakout_multiplier IS NOT NULL`` to skip unprocessed rows.
 *   • ``virals``     — top 5 by views all-time.
 *
 * Both filter to the caller's ``nicheId``, require ``language = 'vi'`` to
 * exclude cross-posted non-Vietnamese content, and require a non-null
 * ``thumbnail_url`` so the rail thumbnails render. Returns empty arrays
 * when ``nicheId`` is null.
 *
 * Cache key includes ``nicheId`` so switching niches refetches.
 */

export type RailVideo = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number;
  posted_at: string | null;
  hook_phrase: string | null;
  breakout_multiplier: number | null;
};

export type TrendsRailVideos = {
  breakouts7d: RailVideo[];
  virals: RailVideo[];
};

const RAIL_LIMIT = 5;
const RAIL_COLS =
  "video_id, thumbnail_url, creator_handle, views, posted_at, hook_phrase, breakout_multiplier";

export const trendsRailKeys = {
  byNiche: (nicheId: number | null) =>
    ["trends_rail_videos", nicheId] as const,
};

export function useTrendsRailVideos(nicheId: number | null) {
  return useQuery<TrendsRailVideos>({
    queryKey: trendsRailKeys.byNiche(nicheId),
    queryFn: async (): Promise<TrendsRailVideos> => {
      if (nicheId == null) return { breakouts7d: [], virals: [] };

      // 30-day window for breakouts — wider than the old 7d so the pool
      // is robust even after a cron gap. breakout_multiplier already
      // normalises for recency via channel-average comparison.
      const cutoff30d = new Date(
        Date.now() - 30 * 24 * 60 * 60 * 1000,
      ).toISOString();

      // Run both queries in parallel; the rail block is render-blocking
      // on the right column so latency parity matters.
      const [breakRes, viralRes] = await Promise.all([
        supabase
          .from("video_corpus")
          .select(RAIL_COLS)
          .eq("niche_id", nicheId)
          .eq("language", "vi")
          .not("thumbnail_url", "is", null)
          .not("breakout_multiplier", "is", null)
          .gte("posted_at", cutoff30d)
          .order("breakout_multiplier", { ascending: false })
          .limit(RAIL_LIMIT),
        supabase
          .from("video_corpus")
          .select(RAIL_COLS)
          .eq("niche_id", nicheId)
          .eq("language", "vi")
          .not("thumbnail_url", "is", null)
          .order("views", { ascending: false })
          .limit(RAIL_LIMIT),
      ]);

      if (breakRes.error) throw breakRes.error;
      if (viralRes.error) throw viralRes.error;

      return {
        breakouts7d: ((breakRes.data ?? []) as RailVideo[]).slice(0, RAIL_LIMIT),
        virals: ((viralRes.data ?? []) as RailVideo[]).slice(0, RAIL_LIMIT),
      };
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
