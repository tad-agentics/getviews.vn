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

/** Exported for unit tests — deterministic slice that rotates over time when pool > limit. */
export function pickRotatingBreakoutWindow<T extends { video_id: string }>(
  rows: T[],
  limit: number,
  nowMs: number,
  rotationMs: number,
): T[] {
  if (rows.length <= limit) return rows.slice(0, limit);
  const bucket = Math.floor(nowMs / rotationMs);
  const maxStart = rows.length - limit;
  const start = maxStart === 0 ? 0 : bucket % (maxStart + 1);
  return rows.slice(start, start + limit);
}

/** How often the visible trio shifts among the top breakout pool (must divide refetch cadence sensibly). */
const HOME_BREAKOUT_ROTATION_MS = 15 * 60 * 1000;

/**
 * Top breakout-style tiles for Home. Strategy:
 * 1) True breakouts (multiplier set) in the last 14 days by ``indexed_at`` (corpus freshness),
 *    niche-scoped or global if no niche. Fetch a **pool** (not only top-3) so we can rotate.
 * 2) If pool still short: same filter but 90-day window.
 * 3) If still short: top by views in niche (or globally) to always surface three tiles when corpus has data.
 *
 * ``pickRotatingBreakoutWindow`` cycles through overlapping high-multiplier rows so the row does not
 * stay frozen on the same three IDs until DB ranks change.
 */
async function fetchTopBreakoutsForHome(
  nicheId: number | null,
  limit: number,
): Promise<BreakoutVideo[]> {
  const now = Date.now();
  const since14 = new Date(now - 14 * 24 * 3600 * 1000).toISOString();
  const since90 = new Date(now - 90 * 24 * 3600 * 1000).toISOString();

  const pool: BreakoutVideo[] = [];
  const seen = new Set<string>();

  const appendUnique = (rows: BreakoutVideo[] | null) => {
    for (const row of rows ?? []) {
      if (seen.has(row.video_id)) continue;
      seen.add(row.video_id);
      pool.push(row);
    }
  };

  // 1) Recent breakouts — indexed_at matches ingest/corpus updates better than created_at row stamp.
  let q1 = supabase
    .from("video_corpus")
    .select(CORPUS_COLS)
    .gte("indexed_at", since14)
    .not("breakout_multiplier", "is", null);
  q1 = withNiche(q1, nicheId);
  const { data: d1, error: e1 } = await q1
    .order("breakout_multiplier", { ascending: false })
    .order("indexed_at", { ascending: false })
    .limit(24);
  if (e1) throw e1;
  appendUnique((d1 ?? []) as BreakoutVideo[]);

  // 2) Older breakouts (multiplier still set)
  if (pool.length < limit) {
    let q2 = supabase
      .from("video_corpus")
      .select(CORPUS_COLS)
      .gte("indexed_at", since90)
      .not("breakout_multiplier", "is", null);
    q2 = withNiche(q2, nicheId);
    const { data: d2, error: e2 } = await q2
      .order("breakout_multiplier", { ascending: false })
      .order("indexed_at", { ascending: false })
      .limit(48);
    if (e2) throw e2;
    appendUnique((d2 ?? []) as BreakoutVideo[]);
  }

  // 3) Top views — fills the row when multipliers are not backfilled yet
  if (pool.length < limit) {
    let q3 = supabase.from("video_corpus").select(CORPUS_COLS);
    q3 = withNiche(q3, nicheId);
    const { data: d3, error: e3 } = await q3
      .order("views", { ascending: false })
      .order("indexed_at", { ascending: false })
      .limit(60);
    if (e3) throw e3;
    appendUnique((d3 ?? []) as BreakoutVideo[]);
  }

  if (pool.length === 0) return [];

  return pickRotatingBreakoutWindow(pool, limit, now, HOME_BREAKOUT_ROTATION_MS);
}

/**
 * Top breakout / high-signal videos for the Home row. When `nicheId` is null,
 * ranks globally so the section still renders before a primary niche is chosen.
 */
export function useTopBreakouts(nicheId: number | null, limit = 3) {
  return useQuery<BreakoutVideo[]>({
    queryKey: ["home", "top_breakouts", nicheId ?? "all", limit],
    queryFn: () => fetchTopBreakoutsForHome(nicheId, limit),
    // Short stale + interval so rotation (15m buckets) and corpus updates surface without a hard refresh.
    staleTime: 2 * 60 * 1000,
    refetchInterval: 4 * 60 * 1000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
