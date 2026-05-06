import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export type CreatorNiche = {
  id: number;
  slug: string;
  name: string;
  /** Onboarding helper text — short Vietnamese explainer per bucket. */
  description: string | null;
  display_order: number;
};

export const creatorNichesKeys = {
  all: () => ["creator_niches"] as const,
};

/**
 * Two-axis niche refactor PR4 (2026-05-10) — replaces ``useNicheTaxonomy``
 * for picker UIs (Onboarding, Settings, Trends pills). Returns the
 * coarse 16-bucket UX-facing taxonomy creators self-identify with.
 *
 * Sorted by ``display_order`` so the picker matches the seeded order
 * in 20260510000000_two_axis_niche_pr1_schema.sql (beauty → fashion →
 * food → lifestyle → comedy → family → education → tech_gaming →
 * business → wellness → fitness → travel → auto → pets_home).
 */
export function useCreatorNiches() {
  return useQuery({
    queryKey: creatorNichesKeys.all(),
    queryFn: async (): Promise<CreatorNiche[]> => {
      const { data, error } = await supabase
        .from("creator_niches")
        .select("id, slug, name_vn, description_vn, display_order")
        .eq("active", true)
        .order("display_order")
        .order("id");
      if (error) throw error;
      return (data ?? []).map((row) => ({
        id: row.id,
        slug: row.slug,
        name: row.name_vn,
        description: row.description_vn,
        display_order: row.display_order,
      }));
    },
    staleTime: 10 * 60_000,
  });
}
