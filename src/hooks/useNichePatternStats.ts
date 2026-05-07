import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/**
 * Aggregate pattern stats for a niche (PR-T2 — Trends pattern-thesis hero).
 *
 * Source: ``video_patterns`` filtered by ``is_active=true`` AND
 * ``niche_spread @> [nicheId]``. Returns:
 *   • ``total`` — active patterns in the niche from a bounded sample (max 200 rows)
 *   • ``patterns_active_this_week`` — head count of patterns with
 *     ``weekly_instance_count > 0`` (pipeline week bucket, not rolling 7d)
 *   • ``fresh`` / ``fresh_pct`` — from the same 200-row sample
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

      const [weekRes, sampleRes] = await Promise.all([
        supabase
          .from("video_patterns")
          .select("*", { count: "planned", head: true })
          .eq("is_active", true)
          .contains("niche_spread", [nicheId])
          .gt("weekly_instance_count", 0),
        supabase
          .from("video_patterns")
          .select("weekly_instance_count_prev")
          .eq("is_active", true)
          .contains("niche_spread", [nicheId])
          .limit(200),
      ]);

      if (sampleRes.error) throw sampleRes.error;

      const patterns_active_this_week = weekRes.error ? null : weekRes.count ?? null;

      const rows = (sampleRes.data ?? []) as Array<{ weekly_instance_count_prev: number | null }>;
      const total = rows.length;
      const fresh = rows.filter(
        (r) => Number(r.weekly_instance_count_prev ?? 0) === 0,
      ).length;
      const fresh_pct =
        total > 0 ? `${Math.round((fresh / total) * 100)}%` : "—";
      return { total, patterns_active_this_week, fresh, fresh_pct };
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
