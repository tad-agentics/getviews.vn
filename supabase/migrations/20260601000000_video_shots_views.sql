-- 2026-06-01 — denormalize ``video_corpus.views`` onto ``video_shots`` so
-- the shot-reference matcher can surface a "256K view" credibility number
-- on each RefClipCard without an extra join. Mirrors the existing
-- denormalization pattern (``creator_handle``, ``thumbnail_url``,
-- ``tiktok_url``, ``hook_type``) — see ``20260510000003_video_shots_table.sql``
-- for rationale: keeping the matcher's lookup query single-table.
--
-- Why "views" matters on the script-shot reference card (per design
-- pack ``screens/script.jsx`` lines 1053-1098): the creator picking which
-- shot to mimic relies on a quality signal — viral references are far
-- more useful than long-tail ones. The numeric "view" pill is the
-- concrete proof that this reference earned its slot.
--
-- ── Schema ──────────────────────────────────────────────────────────
--
-- Nullable BIGINT — views are an int64 in the corpus and we may have
-- ``video_shots`` rows from before this column existed. The matcher
-- treats NULL as "unknown" and the FE shows no view chip.
--
-- ── Backfill ────────────────────────────────────────────────────────
--
-- One-shot UPDATE FROM ``video_corpus``. Covers every existing row in
-- one statement; idempotent (NULL-only WHERE clause guards re-runs).
-- New rows get views populated by the writer
-- (``cloud-run/getviews_pipeline/video_shots_writer.py``).

ALTER TABLE public.video_shots
  ADD COLUMN IF NOT EXISTS views BIGINT;

UPDATE public.video_shots vs
   SET views = vc.views
  FROM public.video_corpus vc
 WHERE vs.video_id = vc.video_id
   AND vs.views IS NULL;

COMMENT ON COLUMN public.video_shots.views IS
  'Denormalized from video_corpus.views at write time — lets the script-shot reference matcher surface "X view" on each RefClipCard without a join. Stale-OK (corpus snapshot at ingest, not live).';
