import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export const formatLifecycleKeys = {
  byNiche: (nicheId: number) => ["format_lifecycle", nicheId] as const,
};

export function useFormatLifecycle(nicheId: number | null) {
  return useQuery({
    queryKey: formatLifecycleKeys.byNiche(nicheId ?? 0),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("format_lifecycle")
        .select("*")
        .eq("niche_id", nicheId!)
        .order("engagement_trend", { ascending: false, nullsFirst: false });
      if (error) throw error;
      return data ?? [];
    },
    enabled: !!nicheId,
    staleTime: 60 * 60_000,
  });
}
