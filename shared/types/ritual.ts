/** Ritual types shared between web (src/) and future mobile screens. */

/** Sound Radar bucket label assigned to a ritual script (L2.2 Sprint 3).
 * Distributed by ``morning_ritual._fetch_sound_recommendations`` from
 * ``trend_velocity.sound_trends``. Only ``accelerating`` and ``peaking``
 * are surfaced — cooling sounds aren't worth recommending. */
export type SoundVelocity = "accelerating" | "peaking";

/** Action-window the FE renders alongside the sound recommendation.
 * Mapped from the velocity bucket — accelerating ⇒ post within 48h,
 * peaking ⇒ this week. ``null``/absent ⇒ no urgency badge rendered. */
export type SoundUrgencyBand = "post_within_48h" | "this_week";

export type RitualScript = {
  hook_type_en: string;
  hook_type_vi: string;
  title_vi: string;
  why_works: string;
  retention_est_pct: number;
  shot_count: number;
  length_sec: number;
  /** Sound Radar enrichment (L2.2 Sprint 3). All five fields are
   * either all present (sound recommendation available for this idea)
   * or all absent (older daily_ritual rows; or niche has no
   * accelerating/peaking sounds this week). FE renders the sound
   * recommendation strip only when ``sound_id`` is non-null. */
  sound_id?: string | null;
  sound_name?: string | null;
  sound_velocity?: SoundVelocity | null;
  sound_delta_pct?: number | null;
  urgency_band?: SoundUrgencyBand | null;
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
