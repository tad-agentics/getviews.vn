import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/**
 * Aggregate pattern stats for a niche (PR-T2 — Trends pattern-thesis hero).
 *
 * Source: ``video_patterns`` filtered by ``is_active=true`` AND
 * ``niche_spread @> [nicheId]``. Returns:
 *   • ``total`` — full count of active patterns for the niche (exact DB count)
 *   • ``patterns_active_this_week`` — head count of patterns with
 *     ``weekly_instance_count > 0`` (pipeline week bucket, not rolling 7d)
 *   • ``fresh`` / ``fresh_pct`` — patterns with ``weekly_instance_count_prev``
 *     null or 0, over the same filtered set (exact counts)
 *
 * Returns ``null`` when ``nicheId`` is null.
 */
export type NichePatternStats = {
  total: number;
  /** Patterns with instances in the current stats week (hero H1 accent). */
  patterns_active_this_week: number | null;
  fresh: number;
  fresh_pct: string;
};

export const nichePatternStatsKeys = {
  byNiche: (nicheId: number | null) =>
    ["niche_pattern_stats", nicheId] as const,
};

export function useNichePatternStats(nicheId: number | null) {
  return useQuery<NichePatternStats | null>({
    queryKey: nichePatternStatsKeys.byNiche(nicheId),
    queryFn: async (): Promise<NichePatternStats | null> => {
      if (nicheId == null) return null;

      const [weekRes, totalRes, freshRes] = await Promise.all([
        supabase
          .from("video_patterns")
          .select("*", { count: "exact", head: true })
          .eq("is_active", true)
          .contains("niche_spread", [nicheId])
          .gt("weekly_instance_count", 0),
        supabase
          .from("video_patterns")
          .select("*", { count: "exact", head: true })
          .eq("is_active", true)
          .contains("niche_spread", [nicheId]),
        supabase
          .from("video_patterns")
          .select("*", { count: "exact", head: true })
          .eq("is_active", true)
          .contains("niche_spread", [nicheId])
          .or("weekly_instance_count_prev.is.null,weekly_instance_count_prev.eq.0"),
      ]);

      if (totalRes.error) throw totalRes.error;
      if (freshRes.error) throw freshRes.error;

      const patterns_active_this_week = weekRes.error ? null : weekRes.count ?? null;

      const total = totalRes.count ?? 0;
      const fresh = freshRes.count ?? 0;
      const fresh_pct = total > 0 ? `${Math.round((fresh / total) * 100)}%` : "—";
      return { total, patterns_active_this_week, fresh, fresh_pct };
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
