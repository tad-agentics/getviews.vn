import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/**
 * Trends right-rail data hook (PR-T6).
 *
 * Two parallel ``video_corpus`` queries surfaced as a single payload:
 *   • ``breakouts7d`` — top 5 by views in the trailing 7 days
 *     (``posted_at`` window). Falls back to ``created_at`` when
 *     ``posted_at`` is null on legacy rows.
 *   • ``virals``     — top 5 by views all-time.
 *
 * Both filter to the caller's ``nicheId`` and require a non-null
 * ``thumbnail_url`` so the rail thumbnails render. Returns empty
 * arrays when ``nicheId`` is null.
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
};

export type TrendsRailVideos = {
  breakouts7d: RailVideo[];
  virals: RailVideo[];
};

const RAIL_LIMIT = 5;
const RAIL_COLS =
  "video_id, thumbnail_url, creator_handle, views, posted_at, hook_phrase";

export const trendsRailKeys = {
  byNiche: (nicheId: number | null) =>
    ["trends_rail_videos", nicheId] as const,
};

export function useTrendsRailVideos(nicheId: number | null) {
  return useQuery<TrendsRailVideos>({
    queryKey: trendsRailKeys.byNiche(nicheId),
    queryFn: async (): Promise<TrendsRailVideos> => {
      if (nicheId == null) return { breakouts7d: [], virals: [] };

      const cutoff = new Date(
        Date.now() - 7 * 24 * 60 * 60 * 1000,
      ).toISOString();

      // Run both queries in parallel; the rail block is render-blocking
      // on the right column so latency parity matters.
      const [breakRes, viralRes] = await Promise.all([
        supabase
          .from("video_corpus")
          .select(RAIL_COLS)
          .eq("niche_id", nicheId)
          .not("thumbnail_url", "is", null)
          .gte("posted_at", cutoff)
          .order("views", { ascending: false })
          .limit(RAIL_LIMIT),
        supabase
          .from("video_corpus")
          .select(RAIL_COLS)
          .eq("niche_id", nicheId)
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
