import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export const nicheTaxonomyKeys = {
  all: () => ["niche_taxonomy"] as const,
};

export function useNicheTaxonomy() {
  return useQuery({
    queryKey: nicheTaxonomyKeys.all(),
    queryFn: async () => {
      const { data, error } = await supabase.from("niche_taxonomy").select("id, name_vn").order("name_vn");
      if (error) throw error;
      return (data ?? []).map((row) => ({ id: row.id, name: row.name_vn }));
    },
    staleTime: 5 * 60_000,
  });
}
