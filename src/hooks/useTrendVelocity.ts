import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export const trendVelocityKeys = {
  byNiche: (nicheId: number) => ["trend_velocity", nicheId] as const,
};

export function useTrendVelocity(nicheId: number | null) {
  return useQuery({
    queryKey: trendVelocityKeys.byNiche(nicheId ?? 0),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("trend_velocity")
        .select("*")
        .eq("niche_id", nicheId!)
        .order("week_start", { ascending: false })
        .limit(10);
      if (error) throw error;
      return data ?? [];
    },
    enabled: !!nicheId,
    staleTime: 60 * 60_000,
  });
}
