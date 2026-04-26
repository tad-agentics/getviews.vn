import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/** Top-K example videos in a pattern — drives the PatternCard 2×2 collage (PR-T3). */
export type PatternVideo = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number;
};

export type TopPattern = {
  id: string;
  display_name: string;
  weekly_instance_count: number;
  weekly_instance_count_prev: number;
  instance_count: number;
  niche_spread: number[];
  /** Average views across all corpus rows tagged with this pattern. */
  avg_views: number | null;
  /** Hook phrase from the most-viewed video in this pattern (display example). */
  sample_hook: string | null;
  /** Top 4 videos in this pattern by view count (PR-T3). Empty array when no
   *  corpus rows tagged with the pattern are available. */
  videos: PatternVideo[];
};

/**
 * Top video_patterns whose niche_spread contains the user's niche, plus
 * derived avg-views + a sample hook phrase per pattern. Runs two reads:
 *   1. video_patterns — top 50 by weekly_instance_count, filtered client-side
 *      to niche_spread containing the caller's niche.
 *   2. video_corpus — all rows with pattern_id in the top ids, from which we
 *      compute avg views and pick the hook_phrase of the top-viewed row.
 *
 * Small table, single-digit round-trip, good enough for the Home table.
 */
export function useTopPatterns(nicheId: number | null, limit = 6) {
  return useQuery<TopPattern[]>({
    queryKey: ["home", "top_patterns", nicheId, limit],
    queryFn: async () => {
      if (nicheId == null) return [];

      const { data: patternRows, error: pErr } = await supabase
        .from("video_patterns")
        .select(
          "id, display_name, weekly_instance_count, weekly_instance_count_prev, instance_count, niche_spread",
        )
        .eq("is_active", true)
        .order("weekly_instance_count", { ascending: false })
        .limit(50);
      if (pErr) throw pErr;

      const patterns = ((patternRows ?? []) as TopPattern[])
        .filter((r) => (r.niche_spread ?? []).includes(nicheId))
        .slice(0, limit);
      if (patterns.length === 0) return [];

      const ids = patterns.map((p) => p.id);
      const { data: corpusRows, error: cErr } = await supabase
        .from("video_corpus")
        .select("video_id, pattern_id, views, hook_phrase, thumbnail_url, creator_handle")
        .in("pattern_id", ids);
      if (cErr) throw cErr;

      type RowAcc = {
        totalViews: number;
        n: number;
        topViews: number;
        topHook: string | null;
        rows: PatternVideo[];
      };
      const byPattern = new Map<string, RowAcc>();
      for (const row of corpusRows ?? []) {
        const pid = (row as { pattern_id?: string | null }).pattern_id;
        if (!pid) continue;
        const views = Number((row as { views?: number | null }).views ?? 0);
        const hook = (row as { hook_phrase?: string | null }).hook_phrase ?? null;
        const videoId = String((row as { video_id?: string | null }).video_id ?? "");
        const thumbnail = (row as { thumbnail_url?: string | null }).thumbnail_url ?? null;
        const handle = (row as { creator_handle?: string | null }).creator_handle ?? null;
        const acc = byPattern.get(pid) ?? {
          totalViews: 0, n: 0, topViews: 0, topHook: null, rows: [],
        };
        acc.totalViews += views;
        acc.n += 1;
        if (views > acc.topViews) {
          acc.topViews = views;
          acc.topHook = hook;
        }
        if (videoId) {
          acc.rows.push({
            video_id: videoId,
            thumbnail_url: thumbnail,
            creator_handle: handle,
            views,
          });
        }
        byPattern.set(pid, acc);
      }

      return patterns.map((p) => {
        const stat = byPattern.get(p.id);
        // Top 4 videos by views — drives the PR-T3 PatternCard 2×2 collage.
        const videos = stat
          ? [...stat.rows].sort((a, b) => b.views - a.views).slice(0, 4)
          : [];
        return {
          ...p,
          avg_views: stat && stat.n > 0 ? Math.round(stat.totalViews / stat.n) : null,
          sample_hook: stat?.topHook ?? null,
          videos,
        };
      });
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
