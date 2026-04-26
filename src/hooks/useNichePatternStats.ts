import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/**
 * Aggregate pattern stats for a niche (PR-T2 — Trends pattern-thesis hero).
 *
 * Source: ``video_patterns`` filtered by ``is_active=true`` AND
 * ``niche_spread @> [nicheId]``. Returns:
 *   • ``total`` — number of active patterns covering this niche
 *   • ``fresh`` — count of patterns whose ``weekly_instance_count_prev``
 *     was 0 (no instances last week — truly "mới")
 *   • ``fresh_pct`` — string like ``"62%"`` for direct rendering, or
 *     ``"—"`` when total = 0
 *
 * Returns ``null`` when ``nicheId`` is null. The query is bounded
 * (``limit(200)``) to keep response time predictable as the patterns
 * table grows.
 */
export type NichePatternStats = {
  total: number;
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
      const { data, error } = await supabase
        .from("video_patterns")
        .select("weekly_instance_count_prev")
        .eq("is_active", true)
        .contains("niche_spread", [nicheId])
        .limit(200);
      if (error) throw error;
      const rows = (data ?? []) as Array<{ weekly_instance_count_prev: number | null }>;
      const total = rows.length;
      const fresh = rows.filter(
        (r) => Number(r.weekly_instance_count_prev ?? 0) === 0,
      ).length;
      const fresh_pct =
        total > 0 ? `${Math.round((fresh / total) * 100)}%` : "—";
      return { total, fresh, fresh_pct };
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
