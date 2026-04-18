import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

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
        .select("pattern_id, views, hook_phrase")
        .in("pattern_id", ids);
      if (cErr) throw cErr;

      const byPattern = new Map<
        string,
        { totalViews: number; n: number; topViews: number; topHook: string | null }
      >();
      for (const row of corpusRows ?? []) {
        const pid = (row as { pattern_id?: string | null }).pattern_id;
        if (!pid) continue;
        const views = Number((row as { views?: number | null }).views ?? 0);
        const hook = (row as { hook_phrase?: string | null }).hook_phrase ?? null;
        const acc = byPattern.get(pid) ?? {
          totalViews: 0, n: 0, topViews: 0, topHook: null,
        };
        acc.totalViews += views;
        acc.n += 1;
        if (views > acc.topViews) {
          acc.topViews = views;
          acc.topHook = hook;
        }
        byPattern.set(pid, acc);
      }

      return patterns.map((p) => {
        const stat = byPattern.get(p.id);
        return {
          ...p,
          avg_views: stat && stat.n > 0 ? Math.round(stat.totalViews / stat.n) : null,
          sample_hook: stat?.topHook ?? null,
        };
      });
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
