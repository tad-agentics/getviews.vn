import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export type TopPattern = {
  id: string;
  display_name: string;
  weekly_instance_count: number;
  weekly_instance_count_prev: number;
  instance_count: number;
  niche_spread: number[];
};

/**
 * Top video_patterns whose niche_spread contains the user's niche, ranked
 * by weekly_instance_count — feeds HooksTable on the Home screen.
 *
 * Direct Supabase read (RLS lets authenticated users see all active
 * patterns). Filtering by niche_id happens client-side because
 * `niche_spread @> ARRAY[id]` isn't exposed cleanly via postgrest and
 * the pattern table is small (hundreds of rows).
 */
export function useTopPatterns(nicheId: number | null, limit = 6) {
  return useQuery<TopPattern[]>({
    queryKey: ["home", "top_patterns", nicheId, limit],
    queryFn: async () => {
      if (nicheId == null) return [];
      const { data, error } = await supabase
        .from("video_patterns")
        .select(
          "id, display_name, weekly_instance_count, weekly_instance_count_prev, instance_count, niche_spread",
        )
        .eq("is_active", true)
        .order("weekly_instance_count", { ascending: false })
        .limit(50);
      if (error) throw error;
      const rows = (data ?? []) as TopPattern[];
      return rows
        .filter((r) => (r.niche_spread ?? []).includes(nicheId))
        .slice(0, limit);
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
