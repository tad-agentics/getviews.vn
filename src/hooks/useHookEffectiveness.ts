import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export const hookEffectivenessKeys = {
  byNiche: (nicheId: number) => ["hook_effectiveness", nicheId] as const,
};

export function useHookEffectiveness(nicheId: number | null) {
  return useQuery({
    queryKey: hookEffectivenessKeys.byNiche(nicheId ?? 0),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("hook_effectiveness")
        .select("*")
        .eq("niche_id", nicheId!)
        .order("avg_engagement_rate", { ascending: false })
        .limit(10);
      if (error) throw error;
      return data ?? [];
    },
    enabled: !!nicheId,
    staleTime: 60 * 60_000,
  });
}
