-- 2026-05-10 — video_shots: per-scene enriched descriptor table.
--
-- Wave 2.5 Phase A PR #1. Closes the foundation for the "reference
-- videos per script shot" feature: at 10K+ corpus (beta target), a
-- JSONB scan for "find scenes where framing=close_up AND pace=slow
-- AND overlay=bold_center" across analysis_json.scenes[] is too slow
-- for interactive script generation. Promoting shots to their own
-- relational table gives the matcher millisecond queries backed by
-- composite B-tree indexes.
--
-- Relationship to video_corpus:
--   video_corpus.analysis_json.scenes[] stays for legacy readers
--   (the ingest path, the existing diagnosis + video screens). This
--   table is a denormalized, queryable projection maintained by the
--   ingest writer (Phase A PR #4: dual-write).
--
--   1 video → N shots (indexed 0..N-1 by scene_index). ON DELETE
--   CASCADE ties shot lifecycle to the parent video.
--
-- Enrichment dimensions (populated by Phase A PR #2's Gemini prompt
-- update; backfill via Phase A PR #4):
--   framing       — close_up | medium | wide | extreme_close_up
--   pace          — static | slow | medium | fast | cut_heavy
--   overlay_style — none | bold_center | sub_caption | chyron | sticker
--   subject       — face | product | text | action | ambient | mixed
--   motion        — static | handheld | slow_mo | time_lapse | match_cut
--   description   — 12–24 word human-readable gloss of the shot
--
-- Denormalized join columns (copied from video_corpus at write time
-- to keep the matcher's query free of joins):
--   hook_type, creator_handle, thumbnail_url, tiktok_url
--
-- Per-scene frame URL (Phase A PR #3 populates):
--   frame_url — R2-hosted JPG of a representative frame inside
--   [start_s, end_s]. NULL until Phase A PR #3 backfill lands.
--
-- Writer: service_role via cloud-run/getviews_pipeline/corpus_ingest.py
-- dual-write path (Phase A PR #4). No authenticated-role policies;
-- follows the batch_job_runs / gemini_calls service-only pattern.

CREATE TABLE IF NOT EXISTS public.video_shots (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id        TEXT NOT NULL,
  niche_id        INTEGER NOT NULL,
  scene_index     INTEGER NOT NULL,
  start_s         REAL,
  end_s           REAL,

  -- Legacy 4-value taxonomy kept for back-compat with the current
  -- matcher + IntelSceneT in script_generate.py.
  scene_type      TEXT,

  -- Enriched descriptors (added 2026-05-10 by Gemini extraction).
  framing         TEXT,
  pace            TEXT,
  overlay_style   TEXT,
  subject         TEXT,
  motion          TEXT,
  description     TEXT,

  -- Denormalized from video_corpus at write time — keeps the
  -- matcher's lookup query free of joins.
  hook_type       TEXT,
  creator_handle  TEXT,
  thumbnail_url   TEXT,
  tiktok_url      TEXT,

  -- Per-scene representative frame hosted on R2 (Phase A PR #3).
  -- NULL until the backfill re-extraction runs.
  frame_url       TEXT,

  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT video_shots_video_fk
    FOREIGN KEY (video_id) REFERENCES public.video_corpus(video_id)
    ON DELETE CASCADE,

  -- Prevents dup ingest + lets upsert on (video_id, scene_index).
  CONSTRAINT video_shots_video_scene_unique
    UNIQUE (video_id, scene_index),

  CONSTRAINT video_shots_scene_index_nonneg CHECK (scene_index >= 0),
  CONSTRAINT video_shots_start_end_valid
    CHECK (start_s IS NULL OR end_s IS NULL OR start_s <= end_s)
);

-- Hot matcher lookup: "find shots with these descriptors in this niche".
-- Composite B-tree covers the typical AND-filtered query — matcher
-- applies niche_id first (small cardinality), then narrows by 2–3 of
-- the enrichment dimensions.
CREATE INDEX IF NOT EXISTS video_shots_match_idx
  ON public.video_shots (niche_id, framing, pace, overlay_style);

-- Secondary match dimension: hook_type filter.
CREATE INDEX IF NOT EXISTS video_shots_niche_hook_idx
  ON public.video_shots (niche_id, hook_type)
  WHERE hook_type IS NOT NULL;

-- Video-level traversal (e.g. "show me all shots for this video"
-- from the admin panel / debug surface).
CREATE INDEX IF NOT EXISTS video_shots_video_idx
  ON public.video_shots (video_id, scene_index);

ALTER TABLE public.video_shots ENABLE ROW LEVEL SECURITY;
-- No authenticated-role policies; service_role writer + readers only.

COMMENT ON TABLE public.video_shots IS
  'Per-scene enriched descriptors for matcher queries. Denormalized from video_corpus.analysis_json.scenes[] — keeps script shot-reference matching sub-millisecond at 10K+ corpus. Writer: ingest dual-write path + admin re-extract. See Wave 2.5 in artifacts/docs/implementation-plan.md.';

COMMENT ON COLUMN public.video_shots.framing IS
  'close_up | medium | wide | extreme_close_up';
COMMENT ON COLUMN public.video_shots.pace IS
  'static | slow | medium | fast | cut_heavy';
COMMENT ON COLUMN public.video_shots.overlay_style IS
  'none | bold_center | sub_caption | chyron | sticker';
COMMENT ON COLUMN public.video_shots.subject IS
  'face | product | text | action | ambient | mixed';
COMMENT ON COLUMN public.video_shots.motion IS
  'static | handheld | slow_mo | time_lapse | match_cut';
COMMENT ON COLUMN public.video_shots.frame_url IS
  'R2-hosted JPG of a representative frame inside [start_s, end_s]. NULL when not yet extracted.';
