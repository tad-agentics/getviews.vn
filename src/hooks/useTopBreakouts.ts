import { useQuery } from "@tanstack/react-query";
import {
  applyBrowsableCorpusFilter,
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

type BreakoutFilterScope = { contentClassIds: number[]; legacyNicheId: number | null };

async function queryBreakoutPool(
  since: string,
  filterScope: BreakoutFilterScope,
  limit: number,
  eligibleOnly: boolean,
): Promise<BreakoutVideo[]> {
  let q = supabase
    .from("video_corpus")
    .select(CORPUS_COLS)
    .gte("indexed_at", since)
    .gte("breakout_multiplier", 1.0);
  if (eligibleOnly) {
    q = q.eq("reference_eligible", true);
  }
  q = applyBrowsableCorpusFilter(applyVideoCorpusNicheFilter(q, filterScope));
  const { data, error } = await q
    .order("breakout_multiplier", { ascending: false })
    .order("indexed_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return (data ?? []) as BreakoutVideo[];
}

/** Eligible-first with unfiltered fallback (§4.7.5 — mirror W4-4). */
export async function fetchBreakoutPass(
  since: string,
  filterScope: BreakoutFilterScope,
  limit: number,
): Promise<BreakoutVideo[]> {
  const eligible = await queryBreakoutPool(since, filterScope, limit, true);
  if (eligible.length >= limit) return eligible;
  const fallback = await queryBreakoutPool(since, filterScope, limit, false);
  const seen = new Set(eligible.map((r) => r.video_id));
  const merged = [...eligible];
  for (const row of fallback) {
    if (seen.has(row.video_id)) continue;
    seen.add(row.video_id);
    merged.push(row);
  }
  return merged;
}

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

  if (creatorNicheId != null) {
    contentClassIds = await fetchContentClassIdsForCreatorNiche(creatorNicheId);
    if (contentClassIds.length === 0) {
      legacyNicheId = legacyNicheIdForCreatorNiche(creatorNicheId);
    }
  }

  const filterScope = { contentClassIds, legacyNicheId };

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
  appendUnique(await fetchBreakoutPass(since14, filterScope, 24));

  // 2) Older breakouts (multiplier still set and ≥ 1.0)
  if (pool.length < limit) {
    appendUnique(await fetchBreakoutPass(since90, filterScope, 48));
  }

  // 3) Top views — fills the row when multipliers are not backfilled yet
  if (pool.length < limit) {
    let q3 = supabase.from("video_corpus").select(CORPUS_COLS);
    q3 = applyBrowsableCorpusFilter(applyVideoCorpusNicheFilter(q3, filterScope));
    const eligibleViews = await q3
      .eq("reference_eligible", true)
      .order("views", { ascending: false })
      .order("indexed_at", { ascending: false })
      .limit(60);
    if (eligibleViews.error) throw eligibleViews.error;
    appendUnique((eligibleViews.data ?? []) as BreakoutVideo[]);
  }
  if (pool.length < limit) {
    let q3b = supabase.from("video_corpus").select(CORPUS_COLS);
    q3b = applyBrowsableCorpusFilter(applyVideoCorpusNicheFilter(q3b, filterScope));
    const { data: d3, error: e3 } = await q3b
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
