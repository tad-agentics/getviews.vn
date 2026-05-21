import { useQuery } from "@tanstack/react-query";
import {
  applyVideoCorpusNicheFilter,
  fetchContentClassIdsForCreatorNiche,
} from "@/lib/corpusNicheFilter";
import { supabase } from "@/lib/supabase";
import { legacyNicheIdForCreatorNiche } from "@/lib/profileNiches";

export type BreakoutVideo = {
  video_id: string;
  tiktok_url: string;
  thumbnail_url: string | null;
  video_url: string | null;
  creator_handle: string;
  views: number;
  breakout_multiplier: number | null;
  hook_phrase: string | null;
  hook_type: string | null;
  video_duration: number | null;
};

const CORPUS_COLS =
  "video_id, tiktok_url, thumbnail_url, video_url, creator_handle, views, breakout_multiplier, hook_phrase, hook_type, video_duration";

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
 * 1) True breakouts (multiplier set) in the last 14 days, filtered by content_class_id
 *    (all classes mapped to the user's creator niche via the junction table), with legacy
 *    niche_id as a safety fallback and global as a last resort.
 * 2) If pool still short: same filter but 90-day window.
 * 3) If still short: top by views (same filter) to always surface three tiles.
 *
 * ``pickRotatingBreakoutWindow`` cycles through overlapping high-multiplier rows so the row does not
 * stay frozen on the same three IDs until DB ranks change.
 */
async function fetchTopBreakoutsForHome(
  creatorNicheId: number | null,
  limit: number,
): Promise<BreakoutVideo[]> {
  const now = Date.now();
  const since14 = new Date(now - 14 * 24 * 3600 * 1000).toISOString();
  const since90 = new Date(now - 90 * 24 * 3600 * 1000).toISOString();

  // Resolve the sharpest available filter upfront.
  let contentClassIds: number[] = [];
  let legacyNicheId: number | null = null;

  let aggregateSampleSize = 0;
  if (creatorNicheId != null) {
    contentClassIds = await fetchContentClassIdsForCreatorNiche(creatorNicheId);
    if (contentClassIds.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: ccRows } = await (supabase as any)
        .from("content_class_intelligence")
        .select("sample_size")
        .in("content_class_id", contentClassIds);
      aggregateSampleSize = ((ccRows ?? []) as { sample_size: number | null }[]).reduce(
        (sum, r) => sum + (typeof r.sample_size === "number" && r.sample_size > 0 ? r.sample_size : 0),
        0,
      );
    }
    // If the junction table is empty or the table hasn't been seeded for this niche,
    // fall back to the legacy 1:1 niche mapping.
    if (contentClassIds.length === 0) {
      legacyNicheId = legacyNicheIdForCreatorNiche(creatorNicheId);
    }
  }

  const filterScope = { contentClassIds, legacyNicheId, aggregateSampleSize };

  const pool: BreakoutVideo[] = [];
  const seen = new Set<string>();

  const appendUnique = (rows: BreakoutVideo[] | null) => {
    for (const row of rows ?? []) {
      if (seen.has(row.video_id)) continue;
      seen.add(row.video_id);
      pool.push(row);
    }
  };

  // 1) Recent breakouts — multiplier must be ≥ 1.0 (beat channel average).
  //    indexed_at matches ingest/corpus updates better than created_at row stamp.
  let q1 = supabase
    .from("video_corpus")
    .select(CORPUS_COLS)
    .gte("indexed_at", since14)
    .gte("breakout_multiplier", 1.0);
  q1 = applyVideoCorpusNicheFilter(q1, filterScope);
  const { data: d1, error: e1 } = await q1
    .order("breakout_multiplier", { ascending: false })
    .order("indexed_at", { ascending: false })
    .limit(24);
  if (e1) throw e1;
  appendUnique((d1 ?? []) as BreakoutVideo[]);

  // 2) Older breakouts (multiplier still set and ≥ 1.0)
  if (pool.length < limit) {
    let q2 = supabase
      .from("video_corpus")
      .select(CORPUS_COLS)
      .gte("indexed_at", since90)
      .gte("breakout_multiplier", 1.0);
    q2 = applyVideoCorpusNicheFilter(q2, filterScope);
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
    q3 = applyVideoCorpusNicheFilter(q3, filterScope);
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
 * Top breakout / high-signal videos for the Home row. When `creatorNicheId` is null,
 * ranks globally so the section still renders before a primary niche is chosen.
 *
 * Filters by content_class_id IN (all classes for the creator's niche) via the
 * creator_niche_content_classes junction — sharper than the legacy 1:1 niche_id mapping.
 */
export function useTopBreakouts(creatorNicheId: number | null, limit = 3) {
  return useQuery<BreakoutVideo[]>({
    queryKey: ["home", "top_breakouts", creatorNicheId ?? "all", limit],
    queryFn: () => fetchTopBreakoutsForHome(creatorNicheId, limit),
    // Short stale + interval so rotation (15m buckets) and corpus updates surface without a hard refresh.
    staleTime: 2 * 60 * 1000,
    refetchInterval: 4 * 60 * 1000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}
