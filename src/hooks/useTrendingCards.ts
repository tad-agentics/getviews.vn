import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export interface TrendingCardRow {
  id: string;
  niche_id: number;
  title: string;
  description: string;
  signal: string;
  hook_type: string | null;
  video_ids: string[] | null;
  corpus_cite: string | null;
  computed_at: string | null;
  week_of: string;
}

const SIGNAL_PRIORITY: Record<string, number> = {
  rising: 0,
  early: 1,
  stable: 2,
  declining: 3,
};

export function useTrendingCards(nicheId: number | null) {
  return useQuery({
    queryKey: ["trending_cards_cross", nicheId] as const,
    queryFn: async (): Promise<TrendingCardRow[]> => {
      const { data, error } = await supabase
        .from("trending_cards")
        .select("*")
        .order("week_of", { ascending: false })
        .limit(120);

      if (error) {
        console.warn("[useTrendingCards]", error.message);
        return [];
      }

      const rows = (data ?? []) as TrendingCardRow[];
      if (rows.length === 0) return [];

      const latestWeek = rows[0]?.week_of;
      if (latestWeek == null) return [];

      const latestRows = rows.filter((r) => r.week_of === latestWeek);

      // Deduplicate by hook_type — same hook in multiple niches → keep best card.
      // When nicheId is set: selected niche wins over any other niche, then signal.
      // When nicheId is null: no niche priority — keep the best signal across all niches.
      const byHookType = new Map<string, TrendingCardRow>();
      for (const row of latestRows) {
        const key = row.hook_type ?? `__unique_${row.id}`;
        const existing = byHookType.get(key);
        if (!existing) {
          byHookType.set(key, row);
          continue;
        }
        if (nicheId != null) {
          const rowIsSelected = row.niche_id === nicheId;
          const existingIsSelected = existing.niche_id === nicheId;
          if (rowIsSelected && !existingIsSelected) {
            byHookType.set(key, row);
            continue;
          }
          if (existingIsSelected) continue;
        }
        // Both cross-niche (or nicheId is null): keep whichever has better signal.
        const rp = SIGNAL_PRIORITY[row.signal] ?? 99;
        const ep = SIGNAL_PRIORITY[existing.signal] ?? 99;
        if (rp < ep) byHookType.set(key, row);
      }

      // Sort: when a niche is selected, its cards float first; then by signal strength.
      return [...byHookType.values()]
        .sort((a, b) => {
          if (nicheId != null) {
            const aSelected = a.niche_id === nicheId ? 0 : 1;
            const bSelected = b.niche_id === nicheId ? 0 : 1;
            if (aSelected !== bSelected) return aSelected - bSelected;
          }
          return (SIGNAL_PRIORITY[a.signal] ?? 99) - (SIGNAL_PRIORITY[b.signal] ?? 99);
        })
        .slice(0, 8);
    },
    enabled: true,
    staleTime: 30 * 60 * 1000,
  });
}
