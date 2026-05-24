import { useQuery } from "@tanstack/react-query";
import { applyBrowsableCorpusFilter } from "@/lib/corpusNicheFilter";
import { supabase } from "@/lib/supabase";

export type CrossNicheBreakout = {
  video_id: string;
  tiktok_url: string;
  thumbnail_url: string | null;
  creator_handle: string;
  views: number;
  breakout_multiplier: number | null;
  content_class_id: number | null;
  hook_phrase: string | null;
};

const COLS =
  "video_id,tiktok_url,thumbnail_url,creator_handle,views,breakout_multiplier,content_class_id,hook_phrase";

export async function fetchCrossNicheBreakouts(
  excludeClassIds: number[],
  limit = 3,
): Promise<CrossNicheBreakout[]> {
  const since14 = new Date(Date.now() - 14 * 24 * 3600 * 1000).toISOString();

  async function run(eligibleOnly: boolean): Promise<CrossNicheBreakout[]> {
    let q = supabase
      .from("video_corpus")
      .select(COLS)
      .gte("indexed_at", since14)
      .gte("breakout_multiplier", 1.5)
      .not("content_class_id", "is", null);
    if (eligibleOnly) {
      q = q.eq("reference_eligible", true);
    }
    q = applyBrowsableCorpusFilter(q);
    if (excludeClassIds.length > 0) {
      q = q.not("content_class_id", "in", `(${excludeClassIds.join(",")})`);
    }
    const { data, error } = await q
      .order("breakout_multiplier", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return (data ?? []) as CrossNicheBreakout[];
  }

  const eligible = await run(true);
  if (eligible.length >= limit) return eligible;
  const fallback = await run(false);
  const seen = new Set(eligible.map((r) => r.video_id));
  const merged = [...eligible];
  for (const row of fallback) {
    if (seen.has(row.video_id)) continue;
    seen.add(row.video_id);
    merged.push(row);
    if (merged.length >= limit) break;
  }
  return merged;
}

/** Wave 3b — breakout videos outside user junction classes (cap 3). */
export function useCrossNicheBreakouts(excludeClassIds: number[], enabled = true) {
  const key = [...excludeClassIds].sort((a, b) => a - b);
  return useQuery({
    queryKey: ["cross_niche_breakouts", key],
    queryFn: () => fetchCrossNicheBreakouts(excludeClassIds, 3),
    // Empty junction → show global breakouts (nothing to exclude).
    enabled,
    staleTime: 5 * 60_000,
  });
}
