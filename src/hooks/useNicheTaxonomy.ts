import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export const nicheTaxonomyKeys = {
  all: () => ["niche_taxonomy"] as const,
};

export function useNicheTaxonomy() {
  return useQuery({
    queryKey: nicheTaxonomyKeys.all(),
    queryFn: async () => {
      const { data, error } = await supabase.from("niche_taxonomy").select("id, name").order("name");
      if (error) throw error;
      return data as { id: number; name: string }[];
    },
    staleTime: 5 * 60_000,
  });
}
