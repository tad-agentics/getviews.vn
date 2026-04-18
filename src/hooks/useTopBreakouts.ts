import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

export type BreakoutVideo = {
  video_id: string;
  tiktok_url: string;
  thumbnail_url: string | null;
  creator_handle: string;
  views: number;
  breakout_multiplier: number | null;
  hook_phrase: string | null;
  hook_type: string | null;
  video_duration: number | null;
};

const CORPUS_COLS =
  "video_id, tiktok_url, thumbnail_url, creator_handle, views, breakout_multiplier, hook_phrase, hook_type, video_duration";

function withNiche<T extends { eq: (a: string, b: number) => T }>(
  q: T,
  nicheId: number | null,
): T {
  if (nicheId == null) return q;
  return q.eq("niche_id", nicheId);
}

/**
 * Top breakout-style tiles for Home. Strategy:
 * 1) True breakouts (multiplier set) in the last 14 days, niche-scoped or global if no niche.
 * 2) If still short: same filter but 90-day window.
 * 3) If still short: top by views in niche (or globally) to always surface three tiles when corpus has data.
 */
async function fetchTopBreakoutsForHome(
  nicheId: number | null,
  limit: number,
): Promise<BreakoutVideo[]> {
  const since14 = new Date(Date.now() - 14 * 24 * 3600 * 1000).toISOString();
  const since90 = new Date(Date.now() - 90 * 24 * 3600 * 1000).toISOString();

  const out: BreakoutVideo[] = [];
  const seen = new Set<string>();

  const pushUnique = (rows: BreakoutVideo[] | null) => {
    for (const row of rows ?? []) {
      if (out.length >= limit) break;
      if (seen.has(row.video_id)) continue;
      seen.add(row.video_id);
      out.push(row);
    }
  };

  // 1) Recent breakouts
  let q1 = supabase
    .from("video_corpus")
    .select(CORPUS_COLS)
    .gte("created_at", since14)
    .not("breakout_multiplier", "is", null);
  q1 = withNiche(q1, nicheId);
  const { data: d1, error: e1 } = await q1
    .order("breakout_multiplier", { ascending: false })
    .limit(limit);
  if (e1) throw e1;
  pushUnique((d1 ?? []) as BreakoutVideo[]);

  // 2) Older breakouts (multiplier still set)
  if (out.length < limit) {
    let q2 = supabase
      .from("video_corpus")
      .select(CORPUS_COLS)
      .gte("created_at", since90)
      .not("breakout_multiplier", "is", null);
    q2 = withNiche(q2, nicheId);
    const { data: d2, error: e2 } = await q2
      .order("breakout_multiplier", { ascending: false })
      .limit(limit * 3);
    if (e2) throw e2;
    pushUnique((d2 ?? []) as BreakoutVideo[]);
  }

  // 3) Top views — fills the row when multipliers are not backfilled yet
  if (out.length < limit) {
    let q3 = supabase.from("video_corpus").select(CORPUS_COLS);
    q3 = withNiche(q3, nicheId);
    const { data: d3, error: e3 } = await q3
      .order("views", { ascending: false })
      .limit(40);
    if (e3) throw e3;
    pushUnique((d3 ?? []) as BreakoutVideo[]);
  }

  return out.slice(0, limit);
}

/**
 * Top breakout / high-signal videos for the Home row. When `nicheId` is null,
 * ranks globally so the section still renders before a primary niche is chosen.
 */
export function useTopBreakouts(nicheId: number | null, limit = 3) {
  return useQuery<BreakoutVideo[]>({
    queryKey: ["home", "top_breakouts", nicheId ?? "all", limit],
    queryFn: () => fetchTopBreakoutsForHome(nicheId, limit),
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
