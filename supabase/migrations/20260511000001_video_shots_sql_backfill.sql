-- 2026-05-11 — video_shots SQL-copy backfill from video_corpus.analysis_json.scenes[].
--
-- Wave 2.5 Phase A PR #4 commit (b). Populates the new video_shots table
-- (migration 20260510000003) from the 17K+ scenes already living inside
-- video_corpus.analysis_json.scenes[] across ~1,540 ingested videos.
--
-- This is the "immediate path" of the hybrid backfill — zero Gemini cost,
-- zero new ffmpeg runs, entirely in-database. The enrichment dimensions
-- (framing / pace / overlay_style / subject / motion / description) only
-- land for rows whose Gemini extraction ran AFTER PR #2 shipped the new
-- schema; for everything before that they'll be NULL and the matcher
-- falls back to the legacy scene_type dimension (documented on Scene).
-- frame_url is always NULL here; Phase A PR #4c's top-500 re-extract
-- path fills it for high-engagement rows.
--
-- Idempotency: INSERT … ON CONFLICT (video_id, scene_index) DO NOTHING.
-- Safe to re-run if this migration partially fails halfway through.
-- The ingest dual-write (PR #4 commit (a)) will keep new rows in sync
-- after this migration completes.
--
-- Filters:
--   * scene must be a JSONB object (jsonb_typeof = 'object')
--   * start + end must be numeric and end > start — matches the
--     video_shots_start_end_valid CHECK constraint
--   * string fields coerced: empty → NULL (matches writer-side coercion
--     in video_shots_writer._coerce_optional_str)

INSERT INTO public.video_shots (
  video_id, niche_id, scene_index,
  start_s, end_s,
  scene_type,
  framing, pace, overlay_style, subject, motion, description,
  hook_type, creator_handle, thumbnail_url, tiktok_url
)
SELECT
  vc.video_id,
  vc.niche_id,
  (s.ord - 1)::int AS scene_index,
  (s.scene->>'start')::real AS start_s,
  (s.scene->>'end')::real   AS end_s,
  NULLIF(btrim(s.scene->>'type'),         '') AS scene_type,
  NULLIF(btrim(s.scene->>'framing'),      '') AS framing,
  NULLIF(btrim(s.scene->>'pace'),         '') AS pace,
  NULLIF(btrim(s.scene->>'overlay_style'),'') AS overlay_style,
  NULLIF(btrim(s.scene->>'subject'),      '') AS subject,
  NULLIF(btrim(s.scene->>'motion'),       '') AS motion,
  NULLIF(btrim(s.scene->>'description'),  '') AS description,
  NULLIF(btrim(vc.hook_type),       '')        AS hook_type,
  NULLIF(btrim(vc.creator_handle),  '')        AS creator_handle,
  NULLIF(btrim(vc.thumbnail_url),   '')        AS thumbnail_url,
  NULLIF(btrim(vc.tiktok_url),      '')        AS tiktok_url
FROM public.video_corpus vc
CROSS JOIN LATERAL jsonb_array_elements(
  COALESCE(vc.analysis_json -> 'scenes', '[]'::jsonb)
) WITH ORDINALITY AS s(scene, ord)
WHERE jsonb_typeof(s.scene) = 'object'
  AND s.scene ? 'start' AND s.scene ? 'end'
  AND (s.scene->>'start') ~ '^-?[0-9]+(\.[0-9]+)?$'
  AND (s.scene->>'end')   ~ '^-?[0-9]+(\.[0-9]+)?$'
  AND (s.scene->>'end')::real > (s.scene->>'start')::real
  AND vc.niche_id IS NOT NULL
ON CONFLICT (video_id, scene_index) DO NOTHING;

-- Post-condition check (logged, not enforced — this is a migration, not a test).
-- Expected at write time: ~17K rows inserted from ~1,540 corpus rows.
DO $$
DECLARE
  v_shots INT;
  v_corpus_scenes BIGINT;
BEGIN
  SELECT COUNT(*) INTO v_shots FROM public.video_shots;
  SELECT COALESCE(SUM(jsonb_array_length(COALESCE(analysis_json->'scenes','[]'::jsonb))), 0)
    INTO v_corpus_scenes FROM public.video_corpus;
  RAISE NOTICE 'video_shots backfill: % rows (out of % scenes in corpus)',
    v_shots, v_corpus_scenes;
END$$;
