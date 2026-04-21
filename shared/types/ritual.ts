/** Ritual types shared between web (src/) and future mobile screens. */

export type RitualScript = {
  hook_type_en: string;
  hook_type_vi: string;
  title_vi: string;
  why_works: string;
  retention_est_pct: number;
  shot_count: number;
  length_sec: number;
};

export type DailyRitual = {
  generated_for_date: string;
  niche_id: number;
  adequacy:
    | "none"
    | "reference_pool"
    | "basic_citation"
    | "niche_norms"
    | "hook_effectiveness"
    | "trend_delta";
  scripts: RitualScript[];
  generated_at: string;
};

/**
 * Machine-readable code returned in the 404 body by GET /home/daily-ritual.
 *
 * - `ritual_no_row` — no row exists yet for this user today (first day or cron pending).
 * - `ritual_niche_stale` — a row exists but for a different niche; next cron will fix it.
 */
export type RitualEmptyReason = "ritual_no_row" | "ritual_niche_stale";

/** Shape of the 404 JSON body from /home/daily-ritual. */
export type RitualErrorBody = {
  code: RitualEmptyReason;
  message: string;
};

/** Resolved fetch outcome (platform-agnostic). */
export type RitualResult =
  | { data: DailyRitual; emptyReason: null }
  | { data: null; emptyReason: RitualEmptyReason };
