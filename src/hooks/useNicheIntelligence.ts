import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export const nicheIntelligenceKeys = {
  all: () => ["niche_intelligence"] as const,
  byNiche: (nicheId: number) => ["niche_intelligence", nicheId] as const,
};

export function useNicheIntelligence(nicheId: number | null) {
  return useQuery({
    queryKey: nicheIntelligenceKeys.byNiche(nicheId ?? 0),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("niche_intelligence")
        .select("*")
        .eq("niche_id", nicheId!)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
    enabled: !!nicheId,
    staleTime: 60 * 60_000, // 1h — batch job runs nightly
  });
}
