import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export type ContentClassIntelligenceRow = {
  content_class_id: number;
  sample_size: number | null;
  median_views?: number | null;
  avg_views?: number | null;
  claim_tier?: string | null;
  computed_at?: string | null;
  video_count_7d?: number | null;
  video_count_prior_7d?: number | null;
  avg_views_7d?: number | null;
  avg_views_prior_7d?: number | null;
  view_velocity?: number | null;
  format_momentum?: number | null;
  lifecycle_stage?: string | null;
  hook_distribution?: Record<string, number> | null;
};

export const contentClassIntelligenceKeys = {
  all: () => ["content_class_intelligence"] as const,
  junction: (classIds: number[]) =>
    ["content_class_intelligence", "junction", [...classIds].sort((a, b) => a - b)] as const,
};

/**
 * Junction-scoped rows from ``content_class_intelligence`` MV.
 * ``aggregateSampleSize`` = sum of ``sample_size`` — gates class-first browse + thin-claim banner.
 */
export function useContentClassIntelligence(contentClassIds: number[]) {
  const sortedKey = [...contentClassIds].sort((a, b) => a - b);
  return useQuery({
    queryKey: contentClassIntelligenceKeys.junction(sortedKey),
    queryFn: async () => {
      if (contentClassIds.length === 0) {
        return {
          rows: [] as ContentClassIntelligenceRow[],
          aggregateSampleSize: 0,
          latestComputedAt: null as string | null,
        };
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (supabase as any)
        .from("content_class_intelligence")
        .select(
          "content_class_id,sample_size,median_views,avg_views,claim_tier,computed_at,video_count_7d,video_count_prior_7d,avg_views_7d,avg_views_prior_7d,view_velocity,format_momentum,lifecycle_stage,hook_distribution",
        )
        .in("content_class_id", contentClassIds);
      if (error) throw error;
      const rows = (data ?? []) as ContentClassIntelligenceRow[];
      const aggregateSampleSize = rows.reduce(
        (sum, r) => sum + (typeof r.sample_size === "number" && r.sample_size > 0 ? r.sample_size : 0),
        0,
      );
      const latestComputedAt = rows.reduce<string | null>((latest, r) => {
        const ts = r.computed_at;
        if (!ts) return latest;
        if (latest == null || ts > latest) return ts;
        return latest;
      }, null);
      return { rows, aggregateSampleSize, latestComputedAt };
    },
    enabled: contentClassIds.length > 0,
    staleTime: 60 * 60_000,
  });
}
