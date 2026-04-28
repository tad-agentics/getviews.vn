import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/** Top-K example videos in a pattern — drives the PatternCard 2×2 collage (PR-T3). */
export type PatternVideo = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number;
  /** Canonical TikTok URL when present — helps derive embed id if ``video_id`` is not numeric. */
  tiktok_url: string | null;
};

/** Single content angle inside a pattern (PatternModal "GÓC CÒN TRỐNG"). */
export type PatternDeckAngle = {
  angle: string;
  filled: number;
  /** ``true`` when no creator has covered this angle yet. */
  gap: boolean;
};

export type TopPattern = {
  id: string;
  display_name: string;
  weekly_instance_count: number;
  weekly_instance_count_prev: number;
  instance_count: number;
  niche_spread: number[];
  /** Average views across all corpus rows tagged with this pattern. */
  avg_views: number | null;
  /** Hook phrase from the most-viewed video in this pattern (display example). */
  sample_hook: string | null;
  /** Top 4 videos in this pattern by view count (PR-T3). Empty array when no
   *  corpus rows tagged with the pattern are available. */
  videos: PatternVideo[];
  /** Most-common ``hook_type`` among this pattern's corpus rows. Used to
   *  look up the niche-level retention proxy below.  */
  dominant_hook_type: string | null;
  /** GIỮ% on PatternCard. Sourced from
   *  ``hook_effectiveness.avg_completion_rate`` for the niche +
   *  ``dominant_hook_type``. Niche-level proxy — not per-pattern.
   *  ``null`` when the lookup fails (no hook_effectiveness row, or
   *  pattern videos lacked a hook_type). */
  avg_retention_pct: number | null;
  /**
   * Deck content synthesized by ``pattern_deck_synth.py`` (nightly).
   * All four fields are ``null`` until the cron has run for this
   * pattern; ``PatternModal`` renders "Đang chuẩn bị" stubs in that
   * state, real content otherwise.
   */
  structure: string[] | null;
  why: string | null;
  careful: string | null;
  angles: PatternDeckAngle[] | null;
};

/** Studio Home hook tier + ``HooksTable`` — shared cap (query key includes this). */
export const STUDIO_HOME_TOP_PATTERNS_LIMIT = 6;

/**
 * Top video_patterns whose niche_spread contains the user's niche, plus
 * derived avg-views + a sample hook phrase per pattern. Runs two reads:
 *   1. video_patterns — top 50 by weekly_instance_count, filtered client-side
 *      to niche_spread containing the caller's niche.
 *   2. video_corpus — all rows with pattern_id in the top ids, from which we
 *      compute avg views and pick the hook_phrase of the top-viewed row.
 *
 * Small table, single-digit round-trip, good enough for the Home table.
 */
export function useTopPatterns(nicheId: number | null, limit = STUDIO_HOME_TOP_PATTERNS_LIMIT) {
  return useQuery<TopPattern[]>({
    queryKey: ["home", "top_patterns", nicheId, limit],
    queryFn: async () => {
      if (nicheId == null) return [];

      // ``structure`` / ``why`` / ``careful`` / ``angles`` come from
      // the deck synthesizer (cron-batch-pattern-decks). Default to
      // null on un-decked rows; the FE PatternModal renders "Đang
      // chuẩn bị" stubs in that case.
      const { data: patternRows, error: pErr } = await supabase
        .from("video_patterns")
        .select(
          "id, display_name, weekly_instance_count, weekly_instance_count_prev, instance_count, niche_spread, structure, why, careful, angles",
        )
        .eq("is_active", true)
        .order("weekly_instance_count", { ascending: false })
        .limit(50);
      if (pErr) throw pErr;

      type PatternRow = TopPattern & { niche_spread?: number[] };
      const patterns = ((patternRows ?? []) as PatternRow[])
        .filter((r) => (r.niche_spread ?? []).includes(nicheId))
        .slice(0, limit);
      if (patterns.length === 0) return [];

      const ids = patterns.map((p) => p.id);
      const { data: corpusRows, error: cErr } = await supabase
        .from("video_corpus")
        .select("video_id, pattern_id, views, hook_phrase, hook_type, thumbnail_url, creator_handle, tiktok_url")
        .in("pattern_id", ids);
      if (cErr) throw cErr;

      type RowAcc = {
        totalViews: number;
        n: number;
        topViews: number;
        topHook: string | null;
        rows: PatternVideo[];
        // hook_type frequency for the dominant-hook-type lookup. Pattern's
        // own niche_spread already pins the niche; we only need the type.
        hookTypeFreq: Map<string, number>;
      };
      const byPattern = new Map<string, RowAcc>();
      for (const row of corpusRows ?? []) {
        const pid = (row as { pattern_id?: string | null }).pattern_id;
        if (!pid) continue;
        const views = Number((row as { views?: number | null }).views ?? 0);
        const hook = (row as { hook_phrase?: string | null }).hook_phrase ?? null;
        const hookType = ((row as { hook_type?: string | null }).hook_type ?? "").trim();
        const videoId = String((row as { video_id?: string | null }).video_id ?? "");
        const thumbnail = (row as { thumbnail_url?: string | null }).thumbnail_url ?? null;
        const handle = (row as { creator_handle?: string | null }).creator_handle ?? null;
        const tiktokUrl = (row as { tiktok_url?: string | null }).tiktok_url ?? null;
        const acc = byPattern.get(pid) ?? {
          totalViews: 0, n: 0, topViews: 0, topHook: null, rows: [],
          hookTypeFreq: new Map<string, number>(),
        };
        acc.totalViews += views;
        acc.n += 1;
        if (views > acc.topViews) {
          acc.topViews = views;
          acc.topHook = hook;
        }
        if (hookType) {
          acc.hookTypeFreq.set(hookType, (acc.hookTypeFreq.get(hookType) ?? 0) + 1);
        }
        if (videoId) {
          acc.rows.push({
            video_id: videoId,
            thumbnail_url: thumbnail,
            creator_handle: handle,
            views,
            tiktok_url: tiktokUrl,
          });
        }
        byPattern.set(pid, acc);
      }

      // Niche-level retention proxy: fetch ``hook_effectiveness`` rows
      // for this niche so each pattern can borrow the avg_completion_rate
      // of its dominant hook_type. One query, in-memory join below.
      // ``hook_effectiveness`` already has a UNIQUE (niche_id, hook_type)
      // constraint (migration 20260509000000) so the lookup is sound.
      let retentionByHookType = new Map<string, number>();
      try {
        const { data: heRows, error: heErr } = await supabase
          .from("hook_effectiveness")
          .select("hook_type, avg_completion_rate")
          .eq("niche_id", nicheId);
        if (heErr) throw heErr;
        for (const row of heRows ?? []) {
          const ht = String((row as { hook_type?: string | null }).hook_type ?? "").trim();
          const cr = Number((row as { avg_completion_rate?: number | null }).avg_completion_rate ?? NaN);
          if (ht && Number.isFinite(cr) && cr > 0) {
            retentionByHookType.set(ht, cr);
          }
        }
      } catch {
        // Non-fatal — pattern card just renders ``"—"`` for GIỮ% when
        // hook_effectiveness is unavailable for this niche.
        retentionByHookType = new Map();
      }

      return patterns.map((p) => {
        const stat = byPattern.get(p.id);
        const videos = stat
          ? [...stat.rows].sort((a, b) => b.views - a.views).slice(0, 4)
          : [];
        // Most-common hook_type wins; ties broken by insertion order.
        let dominantHookType: string | null = null;
        if (stat) {
          let bestCount = 0;
          for (const [ht, count] of stat.hookTypeFreq) {
            if (count > bestCount) {
              bestCount = count;
              dominantHookType = ht;
            }
          }
        }
        const completionRate = dominantHookType
          ? retentionByHookType.get(dominantHookType) ?? null
          : null;
        // ``avg_completion_rate`` is stored as a 0–1 float in
        // ``hook_effectiveness``; surface it as a 0–100 integer pct so
        // PatternCard renders ``64%`` style numbers.
        const retentionPct =
          completionRate != null ? Math.round(completionRate * 100) : null;
        return {
          ...p,
          avg_views: stat && stat.n > 0 ? Math.round(stat.totalViews / stat.n) : null,
          sample_hook: stat?.topHook ?? null,
          videos,
          dominant_hook_type: dominantHookType,
          avg_retention_pct: retentionPct,
          // Explicit ``null`` normalisation — supabase returns
          // ``undefined`` when the row's column is JSON null on
          // un-decked patterns; downstream code branches on null.
          structure: (p as { structure?: string[] | null }).structure ?? null,
          why: (p as { why?: string | null }).why ?? null,
          careful: (p as { careful?: string | null }).careful ?? null,
          angles: (p as { angles?: PatternDeckAngle[] | null }).angles ?? null,
        };
      });
    },
    enabled: nicheId != null,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });
}
